"""
Streamlined database configuration and session management.
"""

import os
from contextlib import contextmanager
from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from dotenv import load_dotenv
from app.utils.logger import logger
from app.exceptions import DatabaseError, ValidationError
import time

# Load environment variables
load_dotenv()

# Database URL (preserve existing configuration)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///data/proposals.db")

# SQLAlchemy configurations
POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "10"))
MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "20"))
POOL_TIMEOUT = int(os.getenv("DB_POOL_TIMEOUT", "30"))
POOL_RECYCLE = int(os.getenv("DB_POOL_RECYCLE", "3600"))
ECHO_SQL = os.getenv("SQL_ECHO", "False").lower() == "true"

# Special handling for SQLite connections
connect_args = {}
if DATABASE_URL.startswith("sqlite:"):
    connect_args["check_same_thread"] = False

# Create engine with builtin connection pooling
engine = create_engine(
    DATABASE_URL,
    pool_size=POOL_SIZE,
    max_overflow=MAX_OVERFLOW,
    pool_timeout=POOL_TIMEOUT,
    pool_recycle=POOL_RECYCLE,
    pool_pre_ping=True,  # Check connection validity before using
    echo=ECHO_SQL,
    connect_args=connect_args,
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create scoped session for thread safety
Session = scoped_session(SessionLocal)

# Create base class for models
Base = declarative_base()

# Session context manager
@contextmanager
def get_db():
    """
    Get a database session for use in a context manager.
    
    Examples:
        with get_db() as db:
            result = db.query(Model).all()
    """
    db = Session()
    try:
        yield db
        db.commit()
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Database integrity error: {str(e)}")
        raise ValidationError(f"Database integrity error: {str(e)}")
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Database error: {str(e)}")
        raise DatabaseError(f"Database error: {str(e)}")
    except Exception as e:
        db.rollback()
        logger.error(f"Unexpected error: {str(e)}")
        raise
    finally:
        db.close()
        Session.remove()

# Function to get a database session (legacy compatibility)
def get_session():
    """Get a database session. Caller is responsible for closing."""
    return Session()

# Function to close a database session (legacy compatibility)
def close_session(session):
    """Close a database session safely."""
    if session:
        try:
            session.close()
        except Exception as e:
            logger.error(f"Error closing session: {str(e)}")
    Session.remove()

# Define reusable session scope decorator
@contextmanager
def session_scope():
    """Legacy compatibility for session scope context manager."""
    with get_db() as session:
        yield session
        
# Initialize database tables
def init_db():
    """Initialize database schema."""
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables initialized")

# Function to check database connection
def check_connection():
    """
    Check if database connection is valid.
    
    Returns:
        tuple: (bool, dict) - Connection status and connection stats
    """
    stats = {"connection_time_ms": 0, "query_time_ms": 0}
    try:
        # Measure connection time
        start_time = time.time()
        conn = engine.connect()
        connection_time = time.time() - start_time
        stats["connection_time_ms"] = round(connection_time * 1000, 2)
        
        # Measure query time
        start_time = time.time()
        conn.execute(text("SELECT 1"))
        query_time = time.time() - start_time
        stats["query_time_ms"] = round(query_time * 1000, 2)
        
        # Close connection
        conn.close()
        
        return True, stats
    except Exception as e:
        logger.error(f"Database connection check failed: {str(e)}")
        return False, stats

# Function to handle database reconnection
def reconnect():
    """
    Reconnect to the database by recreating the engine and session factory.
    This function should be called when database connection is lost.
    """
    global engine, Session, SessionLocal
    
    try:
        # Dispose the current engine
        if engine:
            engine.dispose()
            logger.info("Disposed existing engine connections")
        
        # Create a new engine
        engine = create_engine(
            DATABASE_URL,
            pool_size=POOL_SIZE,
            max_overflow=MAX_OVERFLOW,
            pool_timeout=POOL_TIMEOUT,
            pool_recycle=POOL_RECYCLE,
            pool_pre_ping=True,
            echo=ECHO_SQL,
            connect_args=connect_args,
        )
        
        # Create new session factory
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        
        # Reset scoped session
        if Session:
            Session.remove()
            Session.configure(bind=engine)
        else:
            Session = scoped_session(SessionLocal)
            
        logger.info("Successfully reconnected to database")
        return True
    except Exception as e:
        logger.error(f"Failed to reconnect to database: {str(e)}")
        return False