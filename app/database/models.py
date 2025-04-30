import os
from sqlalchemy import (create_engine, Column, String, Text, 
                          Numeric, Date, TIMESTAMP, JSON, Index)
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.sql import func
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Use declarative_base() for modern SQLAlchemy
Base = declarative_base()

class Prospect(Base):
    __tablename__ = 'prospects'

    id = Column(String, primary_key=True)  # Generated MD5 hash
    source = Column(String, nullable=False, index=True)
    native_id = Column(String, index=True)
    requirement_title = Column(Text)
    requirement_description = Column(Text)
    naics = Column(String, index=True)
    estimated_value = Column(Numeric)
    est_value_unit = Column(String)
    solicitation_date = Column(Date, index=True)
    award_date = Column(Date, index=True)
    office = Column(Text)
    place_city = Column(Text)
    place_state = Column(Text)
    place_country = Column(Text)
    contract_type = Column(Text)
    set_aside = Column(Text)
    loaded_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), index=True)
    extra = Column(JSON)

    # Optional: Add __repr__ for better debugging
    def __repr__(self):
        return f"<Prospect(id='{self.id}', source='{self.source}', title='{self.requirement_title[:30]}...')>"

# Example of how to add explicit indexes if not using inline index=True
# Index('idx_prospects_source', Prospect.source)
# Index('idx_prospects_native_id', Prospect.native_id)
# Index('idx_prospects_naics', Prospect.naics)
# Index('idx_prospects_award_date', Prospect.award_date)
# Index('idx_prospects_solicitation_date', Prospect.solicitation_date)

def create_tables(engine):
    """Creates all tables defined in the Base metadata."""
    try:
        logging.info("Attempting to create tables...")
        Base.metadata.create_all(engine)
        logging.info("Tables checked/created successfully.")
    except Exception as e:
        logging.error(f"Error creating tables: {e}", exc_info=True)
        raise

# You might want a function to get the engine from session.py
# or handle engine creation directly where needed.
# from .session import engine # Example if engine is defined in session.py
# if __name__ == "__main__":
#     # This would require database connection setup
#     # For demonstration purposes only
#     # DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://user:password@host:port/database')
#     # engine = create_engine(DATABASE_URL)
#     # create_tables(engine)
#     pass 