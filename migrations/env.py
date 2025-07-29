import logging
from logging.config import fileConfig
import os

from flask import current_app

from alembic import context

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)
logger = logging.getLogger('alembic.env')

# Get database URL from Flask app config or environment variables
db_url = None

# Try to get from Flask app config first (preferred method)
try:
    db_url = current_app.config.get('SQLALCHEMY_DATABASE_URI')
    if db_url:
        logger.info("Using database URL from Flask app config")
except Exception as e:
    logger.warning(f"Could not get database URL from Flask app config: {e}")

# Fallback to environment variables if Flask app config is not available
if not db_url:
    db_url = os.environ.get('DATABASE_URL')
    if db_url:
        logger.info("Using database URL from DATABASE_URL environment variable")
    else:
        # Try legacy environment variable names
        db_url = os.environ.get('SQLALCHEMY_DATABASE_URI')
        if db_url:
            logger.info("Using database URL from SQLALCHEMY_DATABASE_URI environment variable")

# Log the retrieved database URL for debugging (without exposing passwords)
if db_url:
    safe_url = db_url.split('@')[1] if '@' in db_url else db_url
    logger.info(f"Database URL configured: {safe_url}")
    config.set_main_option('sqlalchemy.url', db_url.replace('%', '%%'))
else:
    # Final fallback: try to get from alembic.ini
    fallback_url = config.get_main_option('sqlalchemy.url')
    if fallback_url and not fallback_url.startswith('#'):
        logger.info("Using database URL from alembic.ini")
    else:
        logger.error("No database URL found! Check DATABASE_URL environment variable or alembic.ini")
        # Don't fail here - let Alembic handle the missing URL error

# Add your model's MetaData object here for 'autogenerate' support.
# This requires models to be imported so metadata is populated on current_app.extensions['migrate'].db
try:
    target_metadata = current_app.extensions['migrate'].db.metadata
except AttributeError:
    logger.error("Could not get metadata from current_app.extensions['migrate'].db. "
                 "Ensure Flask-Migrate is initialized with the db object.")
    target_metadata = None

# Standard callback to prevent empty migrations
def process_revision_directives(context, revision, directives):
    if getattr(config.cmd_opts, 'autogenerate', False):
        script = directives[0]
        if script.upgrade_ops.is_empty():
            directives[:] = []
            logger.info('No changes in schema detected.')

def run_migrations_offline():
    """Run migrations in 'offline' mode.
    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well. By skipping the Engine creation
    we don't even need a DBAPI to be available.
    Calls to context.execute() here emit the given string to the
    script output.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True # Keep this useful addition
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    """Run migrations in 'online' mode.
    In this scenario we need to create an Engine
    and associate a connection with the context.
    """
    # This relies on current_app being available and configured by Flask CLI
    try:
        connectable = current_app.extensions['migrate'].db.engine
        logger.info("Successfully got database engine from Flask-Migrate")
    except AttributeError as e:
        logger.error(f"Could not get engine from current_app.extensions['migrate'].db: {e}")
        logger.error("Ensure Flask-Migrate is initialized properly.")
        return # Cannot proceed
    except Exception as e:
        logger.error(f"Unexpected error getting database engine: {e}")
        return

    try:
        with connectable.connect() as connection:
            logger.info("Database connection established successfully")
            
            configure_args = current_app.extensions['migrate'].configure_args
            if configure_args.get("process_revision_directives") is None:
                configure_args["process_revision_directives"] = process_revision_directives
            
            # Add compare_type to the arguments passed to context.configure
            configure_args['compare_type'] = True

            context.configure(
                connection=connection,
                target_metadata=target_metadata,
                **configure_args
            )

            with context.begin_transaction():
                logger.info("Running database migrations...")
                context.run_migrations()
                logger.info("Database migrations completed successfully")
                
    except Exception as e:
        logger.error(f"Error during migration execution: {e}")
        raise

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
