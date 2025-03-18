from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.exc import SQLAlchemyError, DisconnectionError, IntegrityError, OperationalError, TimeoutError as SQLAlchemyTimeoutError
import os
import logging
from dotenv import load_dotenv
from contextlib import contextmanager
import time
import functools
from sqlalchemy import text
from src.exceptions import DatabaseError, DataIntegrityError, TimeoutError as AppTimeoutError, RetryableError
from src.database.connection_pool import get_engine, get_connection_pool
from src.utils.logging import get_component_logger

# Set up logging using the centralized utility
logger = get_component_logger('database.session_manager')

# Load environment variables
load_dotenv()

# Maximum number of retries for database operations
MAX_RETRIES = int(os.getenv("DB_MAX_RETRIES", 3))
# Delay between retries in seconds
RETRY_DELAY = int(os.getenv("DB_RETRY_DELAY", 1))

# Create session factory using the engine from the connection pool
Session = scoped_session(sessionmaker(bind=get_engine()))

def retry_on_db_error(max_retries=MAX_RETRIES, retry_delay=RETRY_DELAY):
    """Decorator to retry database operations on certain errors"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            while True:
                try:
                    return func(*args, **kwargs)
                except (OperationalError, DisconnectionError) as e:
                    retries += 1
                    if retries > max_retries:
                        logger.error(f"Max retries ({max_retries}) exceeded for database operation: {str(e)}")
                        raise DatabaseError(f"Database operation failed after {max_retries} retries: {str(e)}")
                    
                    logger.warning(f"Database operation failed (attempt {retries}/{max_retries}): {str(e)}")
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    
                    # Check if we need to reconnect
                    if "connection" in str(e).lower() or "disconnect" in str(e).lower():
                        logger.info("Attempting to reconnect to database...")
                        reconnect()
        return wrapper
    return decorator

@retry_on_db_error()
def get_session():
    """Get a database session with retry logic"""
    try:
        session = Session()
        # Test the session with a simple query
        session.execute(text("SELECT 1"))
        return session
    except SQLAlchemyError as e:
        logger.error(f"Error creating database session: {str(e)}")
        Session.remove()
        raise DatabaseError(f"Failed to create database session: {str(e)}")

def close_session(session):
    """Close a database session safely"""
    try:
        if session:
            session.close()
    except Exception as e:
        logger.error(f"Error closing database session: {str(e)}")
    finally:
        Session.remove()

@contextmanager
def session_scope():
    """Context manager for database sessions with automatic commit/rollback"""
    session = None
    try:
        session = get_session()
        yield session
        
        try:
            session.commit()
        except IntegrityError as e:
            logger.error(f"Data integrity error: {str(e)}")
            session.rollback()
            raise DataIntegrityError(f"Data integrity error: {str(e)}")
        except SQLAlchemyTimeoutError as e:
            logger.error(f"Database timeout: {str(e)}")
            session.rollback()
            raise AppTimeoutError(f"Database operation timed out: {str(e)}")
        except OperationalError as e:
            logger.error(f"Database operational error: {str(e)}")
            session.rollback()
            
            # Check if this is a connection error that we should retry
            if "connection" in str(e).lower() or "disconnect" in str(e).lower():
                raise RetryableError(f"Database connection error: {str(e)}")
            
            raise DatabaseError(f"Database operational error: {str(e)}")
        except SQLAlchemyError as e:
            logger.error(f"Database error: {str(e)}")
            session.rollback()
            raise DatabaseError(f"Database error: {str(e)}")
    except Exception as e:
        if session:
            try:
                session.rollback()
            except Exception as rollback_error:
                logger.error(f"Error during session rollback: {str(rollback_error)}")
        raise
    finally:
        close_session(session)

@retry_on_db_error()
def dispose_engine():
    """Dispose of the database engine safely"""
    try:
        get_connection_pool().dispose()
        logger.info("Database engine disposed")
    except Exception as e:
        logger.error(f"Error disposing database engine: {str(e)}")
        raise DatabaseError(f"Failed to dispose database engine: {str(e)}")

@retry_on_db_error(max_retries=5, retry_delay=2)
def reconnect():
    """Reconnect to the database"""
    try:
        logger.info("Reconnecting to database...")
        # Dispose of the current engine and connections
        get_connection_pool().dispose()
        
        # Test the connection
        if get_connection_pool().check_connection():
            logger.info("Successfully reconnected to database")
        else:
            raise DatabaseError("Failed to reconnect to database: connection check failed")
    except Exception as e:
        logger.error(f"Failed to reconnect to database: {str(e)}")
        raise DatabaseError(f"Failed to reconnect to database: {str(e)}")

@retry_on_db_error()
def check_connection():
    """Check if the database connection is valid"""
    return get_connection_pool().check_connection()

def get_connection_stats():
    """Get statistics about the database connection pool"""
    return get_connection_pool().get_stats()

# Import this at the end to avoid circular imports
from sqlalchemy.sql import text 