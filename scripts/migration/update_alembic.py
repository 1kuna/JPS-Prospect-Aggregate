#!/usr/bin/env python3
"""
Update Alembic configuration for PostgreSQL
Updates alembic.ini and migrations/env.py for PostgreSQL compatibility
"""

import os
import sys
import re
from pathlib import Path
import shutil
from datetime import datetime

def backup_file(file_path):
    """Create backup of file before modification"""
    backup_path = f"{file_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy2(file_path, backup_path)
    print(f"Created backup: {backup_path}")
    return backup_path

def update_alembic_ini():
    """Update alembic.ini for PostgreSQL"""
    alembic_ini = Path('alembic.ini')
    
    if not alembic_ini.exists():
        print("ERROR: alembic.ini not found!")
        return False
    
    # Create backup
    backup_file(alembic_ini)
    
    # Read current configuration
    with open(alembic_ini, 'r') as f:
        content = f.read()
    
    # Update SQLAlchemy URL
    # Look for the line that starts with sqlalchemy.url
    pattern = r'sqlalchemy\.url\s*=\s*.*'
    
    # Check if we're in production or development
    if os.path.exists('.env') and os.getenv('FLASK_ENV') == 'production':
        # Use environment variable in production
        replacement = 'sqlalchemy.url = %(DATABASE_URL)s'
        
        # Also need to update the [alembic] section to read from env
        if '[alembic]' in content and 'DATABASE_URL' not in content:
            content = content.replace(
                '[alembic]',
                '[alembic]\n# Read from environment\nDATABASE_URL = postgresql://user:pass@localhost:5432/jps_aggregate'
            )
    else:
        # Use direct PostgreSQL URL for development
        from dotenv import load_dotenv
        load_dotenv('.env')
        db_url = os.getenv('DATABASE_URL', 'postgresql://jps_business_user:password@localhost:5432/jps_aggregate')
        replacement = f'sqlalchemy.url = {db_url}'
    
    # Replace the URL
    content = re.sub(pattern, replacement, content)
    
    # Write updated configuration
    with open(alembic_ini, 'w') as f:
        f.write(content)
    
    print("✓ Updated alembic.ini for PostgreSQL")
    return True

def update_migrations_env():
    """Update migrations/env.py for PostgreSQL compatibility"""
    env_py = Path('migrations/env.py')
    
    if not env_py.exists():
        print("ERROR: migrations/env.py not found!")
        return False
    
    # Create backup
    backup_file(env_py)
    
    # Read current file
    with open(env_py, 'r') as f:
        content = f.read()
    
    # Check if already updated
    if 'postgresql' in content and 'compare_type=True' in content:
        print("✓ migrations/env.py already configured for PostgreSQL")
        return True
    
    # Find the run_migrations_online function
    if 'def run_migrations_online():' in content:
        # Add PostgreSQL-specific imports if not present
        if 'from sqlalchemy.pool import NullPool' not in content:
            # Add import at the top of the file
            import_lines = [
                "from sqlalchemy.pool import NullPool",
                "import os",
                "from dotenv import load_dotenv"
            ]
            
            # Find where to insert imports (after other imports)
            import_insert_pos = content.find('from alembic import context')
            if import_insert_pos != -1:
                # Find the end of the import section
                lines = content[:import_insert_pos].split('\n')
                last_import_line = len(lines) - 1
                
                # Insert new imports
                new_imports = '\n'.join(import_lines) + '\n'
                lines.insert(last_import_line, new_imports)
                
                # Reconstruct content
                content = '\n'.join(lines) + content[import_insert_pos:]
        
        # Update run_migrations_online function
        # Find the function
        func_start = content.find('def run_migrations_online():')
        if func_start != -1:
            # Find the end of the function (next def or end of file)
            func_end = content.find('\ndef ', func_start + 1)
            if func_end == -1:
                func_end = len(content)
            
            # Replace the function
            new_function = '''def run_migrations_online():
    """Run migrations in 'online' mode with PostgreSQL optimizations."""
    
    # Load environment variables
    load_dotenv('.env')
    
    # Get database URL from environment or config
    database_url = os.getenv('DATABASE_URL')
    if database_url:
        config.set_main_option('sqlalchemy.url', database_url)
    
    # Use NullPool to prevent connection issues
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,  # Compare column types
            compare_server_default=True,  # Compare default values
            transaction_per_migration=True,  # Each migration in its own transaction
            render_as_batch=False,  # PostgreSQL doesn't need batch mode
        )

        with context.begin_transaction():
            context.run_migrations()'''
            
            # Replace the function in content
            content = content[:func_start] + new_function + content[func_end:]
    
    # Write updated file
    with open(env_py, 'w') as f:
        f.write(content)
    
    print("✓ Updated migrations/env.py for PostgreSQL")
    return True

def create_postgresql_migration_template():
    """Create a template for PostgreSQL-specific migrations"""
    template_dir = Path('migrations/templates')
    template_dir.mkdir(exist_ok=True)
    
    template_content = '''"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

PostgreSQL-specific migration template
"""
from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

# revision identifiers, used by Alembic.
revision = ${repr(up_revision)}
down_revision = ${repr(down_revision)}
branch_labels = ${repr(branch_labels)}
depends_on = ${repr(depends_on)}


def upgrade():
    """Upgrade database schema"""
    ${upgrades if upgrades else "pass"}
    
    # PostgreSQL-specific operations
    # Example: Create index concurrently (requires PostgreSQL)
    # op.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_example ON table_name(column_name);")
    
    # Example: Add check constraint
    # op.create_check_constraint('check_positive_value', 'table_name', 'column_name > 0')


def downgrade():
    """Downgrade database schema"""
    ${downgrades if downgrades else "pass"}
    
    # PostgreSQL-specific cleanup
    # Example: Drop index
    # op.execute("DROP INDEX IF EXISTS idx_example;")
'''
    
    template_file = template_dir / 'postgresql_migration.py.mako'
    with open(template_file, 'w') as f:
        f.write(template_content)
    
    print("✓ Created PostgreSQL migration template")
    return True

def verify_postgresql_setup():
    """Verify PostgreSQL is properly configured"""
    try:
        import psycopg2
        print("✓ psycopg2 is installed")
    except ImportError:
        print("✗ psycopg2 not installed. Run: pip install psycopg2-binary")
        return False
    
    # Check if we can connect to PostgreSQL
    from dotenv import load_dotenv
    load_dotenv('.env')
    
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        print("✗ DATABASE_URL not found in environment")
        return False
    
    try:
        # Try to connect
        import psycopg2
        conn = psycopg2.connect(db_url)
        conn.close()
        print("✓ Successfully connected to PostgreSQL")
    except Exception as e:
        print(f"✗ Failed to connect to PostgreSQL: {e}")
        return False
    
    return True

def main():
    """Main entry point"""
    print("=== Updating Alembic Configuration for PostgreSQL ===\n")
    
    # Change to project root
    project_root = Path(__file__).parent.parent.parent
    os.chdir(project_root)
    
    success = True
    
    # Update alembic.ini
    if not update_alembic_ini():
        success = False
    
    # Update migrations/env.py
    if not update_migrations_env():
        success = False
    
    # Create PostgreSQL migration template
    if not create_postgresql_migration_template():
        success = False
    
    # Verify setup
    print("\n=== Verifying PostgreSQL Setup ===")
    if not verify_postgresql_setup():
        success = False
    
    if success:
        print("\n✅ Alembic configuration updated successfully!")
        print("\nNext steps:")
        print("1. Review the changes in alembic.ini and migrations/env.py")
        print("2. Run migrations: alembic upgrade head")
        print("3. Create new migrations: alembic revision --autogenerate -m 'description'")
    else:
        print("\n❌ Some updates failed. Please check the errors above.")
        return 1
    
    return 0

if __name__ == '__main__':
    sys.exit(main())