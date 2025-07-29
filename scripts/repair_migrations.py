#!/usr/bin/env python3
"""
Migration Repair Script

This script helps fix migration issues when columns already exist in the database.
It can be run to clean up migration state and ensure the database is in sync.
"""
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import create_app, db
from flask_migrate import stamp
from sqlalchemy import inspect, text
from sqlalchemy.exc import ProgrammingError
import click


def check_table_exists(engine, table_name):
    """Check if a table exists in the database."""
    inspector = inspect(engine)
    return table_name in inspector.get_table_names()


def check_column_exists(engine, table_name, column_name):
    """Check if a column exists in a table."""
    inspector = inspect(engine)
    try:
        columns = [col['name'] for col in inspector.get_columns(table_name)]
        return column_name in columns
    except Exception:
        return False


def get_current_revision(engine):
    """Get the current alembic revision."""
    try:
        result = engine.execute(text("SELECT version_num FROM alembic_version"))
        row = result.first()
        return row[0] if row else None
    except Exception:
        return None


@click.command()
@click.option('--fix', is_flag=True, help='Actually fix issues (default is dry run)')
@click.option('--force-stamp', help='Force stamp a specific revision')
def repair_migrations(fix, force_stamp):
    """Repair migration issues in the database."""
    app = create_app()
    
    with app.app_context():
        engine = db.engine
        
        click.echo("=== Migration Repair Tool ===")
        click.echo(f"Database: {engine.url}")
        click.echo()
        
        # Check current migration state
        current_rev = get_current_revision(engine)
        click.echo(f"Current revision: {current_rev or 'None'}")
        
        # Check if tables exist
        tables_to_check = ['prospects', 'data_sources', 'inferred_prospect_data']
        for table in tables_to_check:
            exists = check_table_exists(engine, table)
            click.echo(f"Table '{table}': {'EXISTS' if exists else 'MISSING'}")
        
        click.echo()
        
        # Check for problematic columns in prospects table
        if check_table_exists(engine, 'prospects'):
            problematic_columns = [
                'estimated_value_text',
                'naics_description',
                'naics_source',
                'estimated_value_min',
                'estimated_value_max',
                'estimated_value_single',
                'primary_contact_email',
                'primary_contact_name',
                'ollama_processed_at',
                'ollama_model_version'
            ]
            
            click.echo("Checking for columns that might cause migration issues:")
            columns_exist = []
            for col in problematic_columns:
                exists = check_column_exists(engine, 'prospects', col)
                if exists:
                    columns_exist.append(col)
                    click.echo(f"  - {col}: EXISTS (might cause duplicate column error)")
                else:
                    click.echo(f"  - {col}: missing")
            
            if columns_exist and not current_rev:
                click.echo()
                click.echo("WARNING: Found existing columns but no migration history!")
                click.echo("This suggests the database was created outside of migrations.")
                
                if fix:
                    click.echo()
                    click.echo("Attempting to fix...")
                    
                    # Create alembic_version table if it doesn't exist
                    try:
                        engine.execute(text("""
                            CREATE TABLE IF NOT EXISTS alembic_version (
                                version_num VARCHAR(32) NOT NULL,
                                CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
                            )
                        """))
                        click.echo("Created alembic_version table")
                    except Exception as e:
                        click.echo(f"Error creating alembic_version table: {e}")
                    
                    # Stamp the database with the appropriate revision
                    if len(columns_exist) == len(problematic_columns):
                        # All columns exist, stamp with the migration that creates them
                        click.echo("Stamping database with revision fbc0e1fbf50d...")
                        stamp(revision='fbc0e1fbf50d')
                        click.echo("Database stamped successfully!")
                    else:
                        click.echo("Only some columns exist. Manual intervention required.")
                else:
                    click.echo()
                    click.echo("Run with --fix to attempt automatic repair")
        
        if force_stamp:
            if fix:
                click.echo(f"\nForce stamping revision: {force_stamp}")
                stamp(revision=force_stamp)
                click.echo("Stamp completed!")
            else:
                click.echo(f"\nWould force stamp revision: {force_stamp}")
                click.echo("Run with --fix to actually stamp")
        
        click.echo("\nDone!")


if __name__ == '__main__':
    repair_migrations()