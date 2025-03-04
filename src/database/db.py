from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get database URL from environment or use default
database_url = os.getenv("DATABASE_URL", "sqlite:///data/proposals.db")

# Create engine with connection pooling settings
engine = create_engine(
    database_url,
    connect_args={"check_same_thread": False},  # Needed for SQLite
    pool_recycle=3600,  # Recycle connections after 1 hour
    pool_pre_ping=True  # Check connection validity before using
)

# Create session factory
session_factory = sessionmaker(bind=engine)
Session = scoped_session(session_factory)

def get_session():
    """Get a database session"""
    return Session()

def close_session(session):
    """Close a database session"""
    session.close()
    Session.remove()

def dispose_engine():
    """Dispose of all connections in the connection pool"""
    engine.dispose()
    
def reconnect():
    """Reconnect to the database if needed"""
    # This will force a new connection on next use
    engine.dispose()
    # Test the connection
    try:
        connection = engine.connect()
        connection.close()
        return True
    except Exception as e:
        print(f"Error reconnecting to database: {e}")
        return False 