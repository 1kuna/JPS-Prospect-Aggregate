from __future__ import annotations
from typing import List, Optional, Dict, Any, Union
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, create_engine, ForeignKey, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, Session
import os
from dotenv import load_dotenv
import datetime

load_dotenv()

Base = declarative_base()

class DataSource(Base):
    """
    Model for tracking different data sources.
    
    This model stores information about each data source that is scraped,
    including its name, URL, and when it was last scraped.
    """
    __tablename__ = 'data_sources'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    url = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    last_scraped = Column(DateTime, nullable=True)
    
    proposals = relationship("Proposal", back_populates="source")
    status_checks = relationship("ScraperStatus", back_populates="source")
    
    def __repr__(self) -> str:
        return f"<DataSource(name='{self.name}', url='{self.url}')>"


class Proposal(Base):
    """
    Model for storing proposal forecast data.
    
    This model stores information about each proposal opportunity,
    including its title, agency, description, and important dates.
    """
    __tablename__ = 'proposals'
    
    id = Column(Integer, primary_key=True)
    source_id = Column(Integer, ForeignKey('data_sources.id'), nullable=False)
    external_id = Column(String(100), nullable=True)
    title = Column(String(255), nullable=False)
    agency = Column(String(100), nullable=True)
    office = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)
    naics_code = Column(String(20), nullable=True)
    estimated_value = Column(Float, nullable=True)
    release_date = Column(DateTime, nullable=True)
    response_date = Column(DateTime, nullable=True)
    contact_info = Column(Text, nullable=True)
    url = Column(String(255), nullable=True)
    status = Column(String(50), nullable=True)
    last_updated = Column(DateTime, default=datetime.datetime.utcnow)
    imported_at = Column(DateTime, default=datetime.datetime.utcnow)
    is_latest = Column(Boolean, default=True)
    
    # Additional fields that might be in the CSV
    contract_type = Column(String(100), nullable=True)
    set_aside = Column(String(100), nullable=True)
    competition_type = Column(String(100), nullable=True)
    solicitation_number = Column(String(100), nullable=True)
    award_date = Column(DateTime, nullable=True)
    place_of_performance = Column(Text, nullable=True)
    incumbent = Column(String(255), nullable=True)
    
    source = relationship("DataSource", back_populates="proposals")
    history = relationship("ProposalHistory", back_populates="proposal")
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the proposal to a dictionary for API responses.
        
        Returns:
            Dict[str, Any]: Dictionary representation of the proposal
        """
        return {
            'id': self.id,
            'source_id': self.source_id,
            'external_id': self.external_id,
            'title': self.title,
            'agency': self.agency,
            'office': self.office,
            'description': self.description,
            'naics_code': self.naics_code,
            'estimated_value': self.estimated_value,
            'release_date': self.release_date.isoformat() if self.release_date else None,
            'response_date': self.response_date.isoformat() if self.response_date else None,
            'contact_info': self.contact_info,
            'url': self.url,
            'status': self.status,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None,
            'imported_at': self.imported_at.isoformat() if self.imported_at else None,
            'contract_type': self.contract_type,
            'set_aside': self.set_aside,
            'competition_type': self.competition_type,
            'solicitation_number': self.solicitation_number,
            'award_date': self.award_date.isoformat() if self.award_date else None,
            'place_of_performance': self.place_of_performance,
            'incumbent': self.incumbent,
            'source_name': self.source.name if self.source else None
        }
    
    def __repr__(self) -> str:
        return f"<Proposal(title='{self.title}', agency='{self.agency}')>"


class ProposalHistory(Base):
    """
    Model for tracking historical proposal data.
    
    This model stores historical versions of proposals to track changes
    over time.
    """
    __tablename__ = 'proposal_history'
    
    id = Column(Integer, primary_key=True)
    proposal_id = Column(Integer, ForeignKey('proposals.id'), nullable=False)
    source_id = Column(Integer, ForeignKey('data_sources.id'), nullable=False)
    external_id = Column(String(100), nullable=True)
    title = Column(String(255), nullable=False)
    agency = Column(String(100), nullable=True)
    office = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)
    naics_code = Column(String(20), nullable=True)
    estimated_value = Column(Float, nullable=True)
    release_date = Column(DateTime, nullable=True)
    response_date = Column(DateTime, nullable=True)
    contact_info = Column(Text, nullable=True)
    url = Column(String(255), nullable=True)
    status = Column(String(50), nullable=True)
    imported_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # Additional fields that might be in the CSV
    contract_type = Column(String(100), nullable=True)
    set_aside = Column(String(100), nullable=True)
    competition_type = Column(String(100), nullable=True)
    solicitation_number = Column(String(100), nullable=True)
    award_date = Column(DateTime, nullable=True)
    place_of_performance = Column(Text, nullable=True)
    incumbent = Column(String(255), nullable=True)
    
    proposal = relationship("Proposal", back_populates="history")
    
    def __repr__(self) -> str:
        return f"<ProposalHistory(proposal_id={self.proposal_id}, imported_at='{self.imported_at}')>"


class ScraperStatus(Base):
    """
    Model for tracking scraper health status.
    
    This model stores information about the health of each scraper,
    including its current status, when it was last checked, and any
    error messages.
    """
    __tablename__ = 'scraper_status'
    
    id = Column(Integer, primary_key=True)
    source_id = Column(Integer, ForeignKey('data_sources.id'), nullable=False)
    status = Column(String(50), nullable=False, default="unknown")  # "working", "not_working", "unknown"
    last_checked = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    response_time = Column(Float, nullable=True)  # in seconds
    
    source = relationship("DataSource", back_populates="status_checks")
    
    def __repr__(self) -> str:
        return f"<ScraperStatus(source_id={self.source_id}, status='{self.status}')>"


def get_engine():
    """
    Get a SQLAlchemy engine instance.
    
    Returns:
        Engine: SQLAlchemy engine instance
    """
    from sqlalchemy import create_engine
    database_url = os.getenv("DATABASE_URL", "sqlite:///data/proposals.db")
    return create_engine(database_url, echo=os.getenv("SQL_ECHO", "False").lower() == "true") 