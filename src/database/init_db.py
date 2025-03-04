import os
import sys
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from .models import Base, DataSource
from dotenv import load_dotenv

# Add the parent directory to the path so we can import from src
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Load environment variables
load_dotenv()

def init_database():
    """Initialize the database and create initial data sources"""
    # Get database URL from environment or use default
    database_url = os.getenv("DATABASE_URL", "sqlite:///data/proposals.db")
    
    # Ensure the data directory exists
    os.makedirs(os.path.dirname(database_url.replace("sqlite:///", "")), exist_ok=True)
    
    # Create engine and tables
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)
    
    # Create a session
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # Add initial data sources if they don't exist
    acquisition_gateway = session.query(DataSource).filter_by(
        name="Acquisition Gateway Forecast"
    ).first()
    
    if not acquisition_gateway:
        acquisition_gateway = DataSource(
            name="Acquisition Gateway Forecast",
            url="https://acquisitiongateway.gov/forecast",
            description="GSA Acquisition Gateway Forecast"
        )
        session.add(acquisition_gateway)
    
    # Commit changes
    session.commit()
    session.close()
    
    print("Database initialized successfully!")

if __name__ == "__main__":
    init_database() 