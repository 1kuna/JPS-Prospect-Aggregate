import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
from contextlib import contextmanager
from pathlib import Path

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
# Get a logger for this module
logger = logging.getLogger(__name__)

# --- SQLite Configuration --- 
default_db_name = "jps_aggregate.db"
# Assume execution from project root or look for .env file location
try:
    # Assumes execution from project root
    BASE_DIR = Path(__file__).resolve().parent.parent.parent
except NameError:
    # Fallback for interactive environments or different execution context
    BASE_DIR = Path('.').resolve() 
    
default_sqlite_path = BASE_DIR / default_db_name
default_sqlite_url = f"sqlite:///{default_sqlite_path.absolute()}"

# Get database URL from environment, fallback to default SQLite path
DATABASE_URL = os.getenv("DATABASE_URL", default_sqlite_url)

engine = None
SessionLocal = None

try:
    # For SQLite, ensure the parent directory exists
    if DATABASE_URL.startswith("sqlite:"):
        db_path_str = DATABASE_URL.split("///", 1)[1]
        db_path = Path(db_path_str)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        logger.info(f"Ensuring database directory exists: {db_path.parent}")

    # echo=False explicitly prevents SQLAlchemy from logging SQL via its internal echo flag
    # connect_args are specific to SQLite to potentially handle thread issues if needed
    engine = create_engine(DATABASE_URL, echo=False, connect_args={"check_same_thread": False})
    
    # Additionally, set the SQLAlchemy engine logger level to WARNING to suppress INFO logs
    # This is belt-and-suspenders approach due to potential multiple basicConfig calls elsewhere
    logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
    
    # Create a configured "Session" class
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    logger.info(f"Database engine and session configured for: {DATABASE_URL}")
except Exception as e:
    logger.error(f"Failed to create database engine for {DATABASE_URL}: {e}", exc_info=True)
    engine = None
    SessionLocal = None

@contextmanager
def get_db():
    """Provide a transactional scope around a series of operations."""
    if not SessionLocal:
        logging.error("Database session not initialized.")
        yield None
        return

    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logging.error(f"Database session error: {e}", exc_info=True)
        db.rollback() # Roll back in case of error
        raise # Re-raise the exception after rollback
    finally:
        db.close() # Always close the session 