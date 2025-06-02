from sqlalchemy import (Column, String, Text,
                          Numeric, Date, TIMESTAMP, JSON, ForeignKey, Integer) # Removed Float
from sqlalchemy.orm import relationship # remove sessionmaker, declarative_base
from sqlalchemy.sql import func
from app.database import db # Import db from flask_sqlalchemy instance

# Logging is now handled by app.utils.logger (Loguru)

class Prospect(db.Model): # Renamed back to Prospect
    __tablename__ = 'prospects' # Renamed back to prospects

    id = Column(String, primary_key=True)  # Generated MD5 hash
    native_id = Column(String, index=True)
    title = Column(Text)
    description = Column(Text)
    agency = Column(Text)
    naics = Column(String, index=True)
    estimated_value = Column(Numeric)
    est_value_unit = Column(String)
    release_date = Column(Date, index=True)
    award_date = Column(Date, index=True)
    award_fiscal_year = Column(Integer, index=True, nullable=True)
    place_city = Column(Text)
    place_state = Column(Text)
    place_country = Column(Text)
    contract_type = Column(Text)
    set_aside = Column(Text)
    loaded_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), index=True)
    extra = Column(JSON)

    # Foreign Key to DataSource
    source_id = Column(Integer, ForeignKey('data_sources.id'), nullable=True, index=True)
    data_source = relationship("DataSource", back_populates="prospects") # Renamed back

    # Relationship to InferredProposalData (one-to-one) - REMOVED
    # inferred_data = relationship(
    #     "InferredProspectData", # Renamed back
    #     back_populates="prospect", # Renamed back
    #     uselist=False,
    #     cascade="all, delete-orphan"
    # )

    def __repr__(self):
        return f"<Prospect(id='{self.id}', source_id='{self.source_id}', title='{self.title[:30] if self.title else ''}...')>" # Renamed from Prospect

    def to_dict(self):
        import math
        
        def clean_value(v):
            """Clean NaN and infinity values from data."""
            if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
                return None
            elif isinstance(v, dict):
                return {k: clean_value(vv) for k, vv in v.items()}
            elif isinstance(v, list):
                return [clean_value(vv) for vv in v]
            return v
        
        return {
            "id": self.id,
            "native_id": self.native_id,
            "title": self.title,
            "description": self.description,
            "agency": self.agency,
            "naics": self.naics,
            "estimated_value": str(self.estimated_value) if self.estimated_value is not None else None,
            "est_value_unit": self.est_value_unit,
            "release_date": self.release_date.isoformat() if self.release_date else None,
            "award_date": self.award_date.isoformat() if self.award_date else None,
            "award_fiscal_year": self.award_fiscal_year,
            "place_city": self.place_city,
            "place_state": self.place_state,
            "place_country": self.place_country,
            "contract_type": self.contract_type,
            "set_aside": self.set_aside,
            "loaded_at": self.loaded_at.isoformat() if self.loaded_at else None,
            "extra": clean_value(self.extra) if self.extra else None,
            "source_id": self.source_id,
            "source_name": self.data_source.name if self.data_source else None,
            # Add inferred data if needed in the future
            # "inferred_data": self.inferred_data.to_dict() if self.inferred_data else None
        }

# Removed InferredProspectData class and its definition

class DataSource(db.Model): # Changed from Base to db.Model
    __tablename__ = 'data_sources'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False, unique=True, index=True)
    url = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    scraper_key = Column(String, nullable=True, index=True) # New column
    last_scraped = Column(TIMESTAMP(timezone=True), nullable=True)
    frequency = Column(String, nullable=True) # e.g., 'daily', 'weekly'

    status_records = relationship("ScraperStatus", back_populates="data_source", cascade="all, delete-orphan")
    prospects = relationship("Prospect", back_populates="data_source") # Renamed back

    def __repr__(self):
        return f"<DataSource(id={self.id}, name='{self.name}')>"

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "url": self.url,
            "description": self.description,
            "scraper_key": self.scraper_key, # Added scraper_key
            "last_scraped": self.last_scraped.isoformat() if self.last_scraped else None,
            "frequency": self.frequency
        }

class ScraperStatus(db.Model): # Changed from Base to db.Model
    __tablename__ = 'scraper_status'

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_id = Column(Integer, ForeignKey('data_sources.id'), nullable=False, index=True)
    status = Column(String, nullable=True) # e.g., 'working', 'failed', 'pending'
    last_checked = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    details = Column(Text, nullable=True) # For error messages or other info

    data_source = relationship("DataSource", back_populates="status_records")

    def __repr__(self):
        return f"<ScraperStatus(id={self.id}, source_id={self.source_id}, status='{self.status}')>"

    def to_dict(self):
        return {
            "id": self.id,
            "source_id": self.source_id,
            "status": self.status,
            "last_checked": self.last_checked.isoformat() if self.last_checked else None,
            "details": self.details
        }

# Removed Index definitions as index=True is used inline.