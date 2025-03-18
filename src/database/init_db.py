import os
import sys
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from src.database.models import Base, DataSource
from dotenv import load_dotenv
from src.utils.logging import get_component_logger
from src.utils.file_utils import ensure_directories

# Set up logging using the centralized utility
logger = get_component_logger('database.init')

# Add the project root directory to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

# Load environment variables
load_dotenv()

def init_database():
    """Initialize the database and create initial data sources"""
    try:
        logger.info("Starting database initialization...")
        
        # Get database URL from environment or use default
        database_url = os.getenv("DATABASE_URL", "sqlite:///data/proposals.db")
        logger.info(f"Using database URL: {database_url}")
        
        # Ensure the data directory exists
        db_path = database_url.replace("sqlite:///", "")
        data_dir = os.path.dirname(db_path)
        ensure_directories(data_dir)
        logger.info(f"Ensured data directory exists: {data_dir}")
        
        # Create engine and tables
        logger.info("Creating database engine...")
        engine = create_engine(database_url)
        
        logger.info("Creating database tables...")
        Base.metadata.create_all(engine)
        logger.info("Database tables created successfully")
        
        # Create a session
        logger.info("Creating database session...")
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Add initial data sources if they don't exist
        logger.info("Checking for existing data sources...")
        
        acquisition_gateway = session.query(DataSource).filter_by(
            name="Acquisition Gateway Forecast"
        ).first()
        
        if not acquisition_gateway:
            logger.info("Creating Acquisition Gateway Forecast data source...")
            acquisition_gateway = DataSource(
                name="Acquisition Gateway Forecast",
                url="https://acquisitiongateway.gov/forecast",
                description="GSA Acquisition Gateway Forecast"
            )
            session.add(acquisition_gateway)
            logger.info("Added Acquisition Gateway Forecast data source")
        
        # Add SSA Contract Forecast data source if it doesn't exist
        ssa_forecast = session.query(DataSource).filter_by(
            name="SSA Contract Forecast"
        ).first()
        
        if not ssa_forecast:
            logger.info("Creating SSA Contract Forecast data source...")
            ssa_forecast = DataSource(
                name="SSA Contract Forecast",
                url="https://www.ssa.gov/foia/contract_forecast.html",
                description="SSA Contract Forecast"
            )
            session.add(ssa_forecast)
            logger.info("Added SSA Contract Forecast data source")
        
        # Commit changes
        logger.info("Committing changes to database...")
        session.commit()
        session.close()
        logger.info("Database initialization completed successfully!")
        
    except Exception as e:
        logger.error(f"Error during database initialization: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise

if __name__ == "__main__":
    init_database() 