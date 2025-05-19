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

# Ensure the Flask app is configured for Alembic.
# This relies on the Flask CLI setting up current_app correctly.
# TheSQLALCHEMY_DATABASE_URI should be correctly picked up from app.config
# (which now uses an absolute path for SQLite).
db_url = current_app.config.get('SQLALCHEMY_DATABASE_URI')

# Log the retrieved database URL for debugging
logger.info(f"SQLALCHEMY_DATABASE_URI from current_app.config: {db_url}")

if db_url:
    config.set_main_option('sqlalchemy.url', db_url.replace('%', '%%'))
else:
    # Fallback or error if not found, though Flask-Migrate usually ensures this.
    logger.warning("SQLALCHEMY_DATABASE_URI not found in current_app.config. "
                   "Migrations might fail if not set in alembic.ini directly.")
    # Alembic will then try to use sqlalchemy.url from alembic.ini if not set here.

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
    except AttributeError:
        logger.error("Could not get engine from current_app.extensions['migrate'].db. "
                     "Ensure Flask-Migrate is initialized properly.")
        return # Cannot proceed

    with connectable.connect() as connection:
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
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
