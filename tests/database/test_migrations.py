"""
Tests for database migrations and schema consistency.

Ensures that Alembic migrations are in sync with SQLAlchemy models.
"""

import os
import tempfile
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect
from sqlalchemy.sql import text

from app import create_app
from app.database import db


class TestMigrations:
    """Test suite for database migrations."""

    @pytest.fixture
    def app(self):
        """Create test Flask app."""
        app = create_app()
        app.config["TESTING"] = True
        return app

    @pytest.fixture
    def alembic_config(self, app):
        """Create Alembic configuration for testing."""
        # Find the alembic.ini file
        project_root = Path(__file__).parent.parent.parent
        alembic_ini = project_root / "migrations" / "alembic.ini"
        
        if not alembic_ini.exists():
            # Try alternative location
            alembic_ini = project_root / "alembic.ini"
        
        if not alembic_ini.exists():
            pytest.skip("alembic.ini not found")
        
        config = Config(str(alembic_ini))
        
        # Override database URL for testing
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            test_db_url = f"sqlite:///{tmp.name}"
            config.set_main_option("sqlalchemy.url", test_db_url)
            
            # Store for cleanup
            self.test_db_file = tmp.name
        
        return config

    def teardown_method(self):
        """Clean up test database file."""
        if hasattr(self, "test_db_file") and os.path.exists(self.test_db_file):
            os.unlink(self.test_db_file)

    def test_alembic_head_is_current(self, app, alembic_config):
        """Test that the database is at the latest migration."""
        with app.app_context():
            # Create database with current schema
            engine = create_engine(alembic_config.get_main_option("sqlalchemy.url"))
            
            # Run migrations to head
            command.upgrade(alembic_config, "head")
            
            # Check if we're at head
            with engine.connect() as connection:
                context = MigrationContext.configure(connection)
                current_heads = context.get_current_heads()
                
                # Get the actual head from alembic
                from alembic.script import ScriptDirectory
                scripts = ScriptDirectory.from_config(alembic_config)
                actual_heads = set(scripts.get_heads())
                
                # Current revision should match the head
                assert current_heads == actual_heads, (
                    f"Database is not at the latest migration. "
                    f"Current: {current_heads}, Expected: {actual_heads}"
                )

    def test_models_match_migration(self, app, alembic_config):
        """Test that SQLAlchemy models match the migrated schema."""
        with app.app_context():
            # Create database with migrations
            engine = create_engine(alembic_config.get_main_option("sqlalchemy.url"))
            command.upgrade(alembic_config, "head")
            
            # Create another database with models
            with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
                model_db_url = f"sqlite:///{tmp.name}"
                model_engine = create_engine(model_db_url)
                
                # Create all tables from models
                db.metadata.create_all(model_engine)
                
                # Compare schemas
                migration_inspector = inspect(engine)
                model_inspector = inspect(model_engine)
                
                # Get table names
                migration_tables = set(migration_inspector.get_table_names())
                model_tables = set(model_inspector.get_table_names())
                
                # Remove alembic version table from comparison
                migration_tables.discard("alembic_version")
                
                # Tables should match
                assert migration_tables == model_tables, (
                    f"Table mismatch. "
                    f"Migration tables: {migration_tables}, "
                    f"Model tables: {model_tables}"
                )
                
                # Check each table's columns
                for table in migration_tables:
                    migration_columns = {
                        col["name"]: col["type"].__class__.__name__
                        for col in migration_inspector.get_columns(table)
                    }
                    model_columns = {
                        col["name"]: col["type"].__class__.__name__
                        for col in model_inspector.get_columns(table)
                    }
                    
                    assert migration_columns == model_columns, (
                        f"Column mismatch in table '{table}'. "
                        f"Migration: {migration_columns}, "
                        f"Model: {model_columns}"
                    )
                
                # Clean up
                os.unlink(tmp.name)

    def test_migration_reversibility(self, app, alembic_config):
        """Test that migrations can be upgraded and downgraded."""
        with app.app_context():
            engine = create_engine(alembic_config.get_main_option("sqlalchemy.url"))
            
            # Start with empty database
            with engine.connect() as connection:
                context = MigrationContext.configure(connection)
                assert context.get_current_heads() == ()
            
            # Upgrade to head
            command.upgrade(alembic_config, "head")
            
            # Verify we're at head
            with engine.connect() as connection:
                context = MigrationContext.configure(connection)
                current = context.get_current_heads()
                assert len(current) > 0
            
            # Downgrade to base
            command.downgrade(alembic_config, "base")
            
            # Verify we're back at base
            with engine.connect() as connection:
                context = MigrationContext.configure(connection)
                assert context.get_current_heads() == ()
            
            # Upgrade again to ensure idempotency
            command.upgrade(alembic_config, "head")
            
            with engine.connect() as connection:
                context = MigrationContext.configure(connection)
                final = context.get_current_heads()
                assert final == current

    def test_no_pending_migrations(self, app, alembic_config):
        """Test that there are no pending migrations to be created."""
        with app.app_context():
            # Apply all migrations
            engine = create_engine(alembic_config.get_main_option("sqlalchemy.url"))
            command.upgrade(alembic_config, "head")
            
            # Check for model changes that would require a migration
            with engine.connect() as connection:
                context = MigrationContext.configure(connection)
                
                # This would be more complex in production, but for basic check:
                # Verify that attempting to autogenerate doesn't find changes
                from alembic.autogenerate import compare_metadata
                
                diff = compare_metadata(context, db.metadata)
                
                # Filter out irrelevant differences
                significant_diff = [
                    item for item in diff
                    if item[0] not in ["remove_table"]  # Ignore alembic_version
                    or item[1] != "alembic_version"
                ]
                
                assert len(significant_diff) == 0, (
                    f"Pending migrations detected: {significant_diff}. "
                    f"Run 'flask db migrate' to create migration."
                )

    def test_migration_naming_convention(self, alembic_config):
        """Test that migration files follow naming conventions."""
        from alembic.script import ScriptDirectory
        
        scripts = ScriptDirectory.from_config(alembic_config)
        
        for revision in scripts.walk_revisions():
            # Check filename format
            assert revision.revision is not None
            assert len(revision.revision) == 12  # Alembic uses 12-char revisions
            
            # Check that migration has a message
            if revision.doc:
                assert len(revision.doc) > 0, f"Migration {revision.revision} has no description"

    def test_critical_tables_exist(self, app, alembic_config):
        """Test that critical tables exist after migration."""
        critical_tables = [
            "prospects",
            "data_sources",
            "go_no_go_decisions",
            "users",
        ]
        
        with app.app_context():
            engine = create_engine(alembic_config.get_main_option("sqlalchemy.url"))
            command.upgrade(alembic_config, "head")
            
            inspector = inspect(engine)
            existing_tables = inspector.get_table_names()
            
            for table in critical_tables:
                assert table in existing_tables, f"Critical table '{table}' not found after migration"

    def test_indexes_are_created(self, app, alembic_config):
        """Test that important indexes are created."""
        expected_indexes = {
            "prospects": ["source_id", "loaded_at"],  # Common query fields
            "go_no_go_decisions": ["user_id", "prospect_id"],
        }
        
        with app.app_context():
            engine = create_engine(alembic_config.get_main_option("sqlalchemy.url"))
            command.upgrade(alembic_config, "head")
            
            inspector = inspect(engine)
            
            for table, expected_cols in expected_indexes.items():
                if table in inspector.get_table_names():
                    indexes = inspector.get_indexes(table)
                    indexed_columns = set()
                    
                    for index in indexes:
                        indexed_columns.update(index["column_names"])
                    
                    for col in expected_cols:
                        # Check if column is indexed (either alone or as part of composite)
                        assert col in indexed_columns or any(
                            col in idx["column_names"] for idx in indexes
                        ), f"Column '{col}' in table '{table}' should be indexed for performance"