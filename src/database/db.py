from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.exc import SQLAlchemyError, DisconnectionError, IntegrityError, OperationalError, TimeoutError as SQLAlchemyTimeoutError
import os
import logging
from dotenv import load_dotenv
from contextlib import contextmanager
import time
from sqlalchemy import text
from src.exceptions import DatabaseError, DataIntegrityError, TimeoutError as AppTimeoutError, RetryableError

# Set up logging
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Get database URL from environment or use default
database_url = os.getenv("DATABASE_URL", "sqlite:///data/proposals.db")

# Create engine with improved connection pooling settings
engine = create_engine(
    database_url,
    connect_args={"check_same_thread": False} if database_url.startswith('sqlite') else {},
    pool_recycle=3600,  # Recycle connections after 1 hour
    pool_pre_ping=True,  # Check connection validity before using
    pool_size=10,  # Maximum number of connections to keep in the pool
    max_overflow=20,  # Maximum number of connections to create above pool_size
    pool_timeout=30,  # Timeout for getting a connection from the pool
    echo=os.getenv("SQL_ECHO", "False").lower() == "true"  # Log SQL queries if enabled
)

# Add event listeners for connection pooling
@event.listens_for(engine, "connect")
def connect(dbapi_connection, connection_record):
    """Log when a connection is created"""
    logger.debug("Database connection established")

@event.listens_for(engine, "checkout")
def checkout(dbapi_connection, connection_record, connection_proxy):
    """Verify that the connection is still valid when it's checked out from the pool"""
    logger.debug("Database connection checked out from pool")
    connection_record.info.setdefault('checkout_time', time.time())

@event.listens_for(engine, "checkin")
def checkin(dbapi_connection, connection_record):
    """Log when a connection is returned to the pool"""
    logger.debug("Database connection returned to pool")
    checkout_time = connection_record.info.get('checkout_time')
    if checkout_time is not None:
        connection_record.info.pop('checkout_time')
        logger.debug(f"Connection was checked out for {time.time() - checkout_time:.2f} seconds")

# Define ping function for SQLite
def sqlite_ping(dbapi_connection):
    """Check if a SQLite connection is still valid"""
    try:
        dbapi_connection.execute(text("SELECT 1"))
        return True
    except Exception:
        return False

# Register the ping function for SQLite
if database_url.startswith('sqlite'):
    @event.listens_for(engine, "engine_connect")
    def ping_connection(connection, branch):
        """Ping the connection to ensure it's still valid"""
        if branch:
            # Don't ping on checkout for a branch connection
            return

        # Check if the connection is valid
        try:
            # Run a simple query
            connection.scalar(text("SELECT 1"))
        except Exception as e:
            logger.warning(f"Connection invalid: {e}")
            # Reconnect
            connection.connection.close()
            raise DisconnectionError("Connection invalid")

# Create session factory with better error handling
session_factory = sessionmaker(bind=engine)
Session = scoped_session(session_factory)

def get_session():
    """Get a database session with retry logic"""
    max_retries = 3
    retry_delay = 1  # seconds
    
    for attempt in range(max_retries):
        try:
            session = Session()
            # Test the connection with a simple query
            session.execute(text("SELECT 1"))
            return session
        except SQLAlchemyError as e:
            logger.warning(f"Error getting database session (attempt {attempt+1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                # Close any existing session
                try:
                    session.close()
                except:
                    pass
                
                # Dispose the engine to force new connections
                engine.dispose()
                
                # Wait before retrying
                time.sleep(retry_delay * (2 ** attempt))  # Exponential backoff
            else:
                # Last attempt failed, re-raise the exception
                logger.error(f"Failed to get database session after {max_retries} attempts")
                raise

def close_session(session):
    """Close a database session safely"""
    try:
        session.close()
        Session.remove()
        logger.debug("Database session closed")
    except Exception as e:
        logger.warning(f"Error closing database session: {e}")

@contextmanager
def session_scope():
    """Provide a transactional scope around a series of operations with improved error handling.
    
    Usage:
        with session_scope() as session:
            # do database operations with session
            # session is automatically committed or rolled back
    """
    session = get_session()
    try:
        yield session
        try:
            session.commit()
            logger.debug("Database transaction committed")
        except IntegrityError as e:
            logger.warning(f"Data integrity error: {e}")
            session.rollback()
            # Convert SQLAlchemy IntegrityError to our custom DataIntegrityError
            error_msg = str(e)
            if "unique constraint" in error_msg.lower():
                raise DataIntegrityError("A record with this information already exists", payload={"original_error": error_msg})
            elif "foreign key constraint" in error_msg.lower():
                raise DataIntegrityError("Referenced record does not exist", payload={"original_error": error_msg})
            else:
                raise DataIntegrityError(f"Data integrity error: {error_msg}", payload={"original_error": error_msg})
        except OperationalError as e:
            logger.warning(f"Database operational error: {e}")
            session.rollback()
            error_msg = str(e)
            if "deadlock" in error_msg.lower():
                raise RetryableError("Database deadlock detected, please retry your operation", 
                                    payload={"original_error": error_msg, "retry_suggested": True})
            elif "timeout" in error_msg.lower() or "timed out" in error_msg.lower():
                raise AppTimeoutError("Database operation timed out", 
                                    payload={"original_error": error_msg, "retry_suggested": True})
            else:
                raise DatabaseError(f"Database operational error: {error_msg}", 
                                   payload={"original_error": error_msg})
        except SQLAlchemyTimeoutError as e:
            logger.warning(f"Database timeout error: {e}")
            session.rollback()
            raise AppTimeoutError("Database operation timed out", 
                                payload={"original_error": str(e), "retry_suggested": True})
        except SQLAlchemyError as e:
            logger.warning(f"Database error: {e}")
            session.rollback()
            raise DatabaseError(f"Database error: {str(e)}", 
                               payload={"original_error": str(e)})
    except (DatabaseError, DataIntegrityError, AppTimeoutError, RetryableError):
        # Re-raise our custom exceptions without modification
        raise
    except Exception as e:
        logger.warning(f"Rolling back database transaction due to error: {e}")
        session.rollback()
        # Convert generic exceptions to DatabaseError
        raise DatabaseError(f"Unexpected error during database operation: {str(e)}", 
                           payload={"original_error": str(e)})
    finally:
        close_session(session)

def dispose_engine():
    """Dispose of all connections in the connection pool"""
    try:
        engine.dispose()
        logger.info("Database engine disposed")
    except Exception as e:
        logger.error(f"Error disposing database engine: {e}")

def reconnect():
    """Reconnect to the database if needed"""
    try:
        # Dispose the engine to force new connections
        engine.dispose()
        
        # Test the connection
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        
        logger.info("Database reconnection successful")
        return True
    except Exception as e:
        logger.error(f"Error reconnecting to database: {e}")
        return False

def check_connection():
    """Check if the database connection is working"""
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"Database connection check failed: {e}")
        return False

# Import this at the end to avoid circular imports
from sqlalchemy.sql import text 