import os
from sqlalchemy import (create_engine, Column, String, Text, 
                          Numeric, Date, TIMESTAMP, JSON, Index,
                          ForeignKey, Float, Integer)
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
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
    award_fiscal_year = Column(Integer, index=True, nullable=True)
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

class InferredProspectData(Base):
    __tablename__ = 'inferred_prospect_data'

    prospect_id = Column(String, ForeignKey('prospects.id'), primary_key=True)
    inferred_requirement_title = Column(Text, nullable=True)
    inferred_requirement_description = Column(Text, nullable=True)
    inferred_naics = Column(String, nullable=True)
    # Use Float for inferred numeric values, matching the schema created by the temp script
    # SQLAlchemy Numeric requires precision/scale, Float is simpler for SQLite/general use here
    inferred_estimated_value = Column(Float, nullable=True) 
    inferred_est_value_unit = Column(String, nullable=True)
    # Store inferred dates as Text for flexibility, consistent with temp script
    inferred_solicitation_date = Column(Text, nullable=True)
    inferred_award_date = Column(Text, nullable=True)
    inferred_office = Column(Text, nullable=True)
    inferred_place_city = Column(Text, nullable=True)
    inferred_place_state = Column(Text, nullable=True)
    inferred_place_country = Column(Text, nullable=True)
    inferred_contract_type = Column(Text, nullable=True)
    inferred_set_aside = Column(Text, nullable=True)
    inferred_at = Column(TIMESTAMP(timezone=False), server_default=func.now(), onupdate=func.now())
    inferred_by_model = Column(String, nullable=True)

    # Define the relationship back to Prospect (optional but useful for ORM queries)
    prospect = relationship("Prospect", back_populates="inferred_data")

    def __repr__(self):
        return f"<InferredProspectData(prospect_id='{self.prospect_id}')>"

# Need to add the corresponding relationship in the Prospect model
Prospect.inferred_data = relationship(
    "InferredProspectData", 
    back_populates="prospect", 
    uselist=False, # One-to-one relationship
    cascade="all, delete-orphan" # Optional: delete inferred data if prospect is deleted
)

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