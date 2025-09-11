from datetime import timezone
UTC = timezone.utc

from sqlalchemy import (
    JSON,
    TIMESTAMP,
    Column,
    Date,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import db


class Prospect(db.Model):
    __tablename__ = "prospects"

    id = Column(String, primary_key=True)  # Generated MD5 hash
    native_id = Column(String, index=True)
    title = Column(Text, index=True)
    ai_enhanced_title = Column(Text)
    description = Column(Text, index=True)
    agency = Column(Text, index=True)
    naics = Column(String, index=True)
    naics_description = Column(String(200))
    naics_source = Column(String(20), index=True)  # 'original', 'llm_inferred', 'llm_enhanced'
    estimated_value = Column(Numeric)
    est_value_unit = Column(String)
    estimated_value_text = Column(String(100))
    estimated_value_min = Column(Numeric(15, 2))
    estimated_value_max = Column(Numeric(15, 2))
    estimated_value_single = Column(Numeric(15, 2), index=True)
    release_date = Column(Date, index=True)
    award_date = Column(Date, index=True)
    award_fiscal_year = Column(Integer, index=True, nullable=True)
    place_city = Column(Text, index=True)
    place_state = Column(Text, index=True)
    place_country = Column(Text)
    contract_type = Column(Text)
    set_aside = Column(Text)
    set_aside_standardized = Column(String(50), index=True)
    set_aside_standardized_label = Column(String(100))
    primary_contact_email = Column(String(100), index=True)
    primary_contact_name = Column(String(100))
    loaded_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), index=True)
    ollama_processed_at = Column(TIMESTAMP(timezone=True), index=True)
    ollama_model_version = Column(String(50))
    enhancement_status = Column(String(20), index=True, default="idle")
    enhancement_started_at = Column(TIMESTAMP(timezone=True), index=True)
    enhancement_user_id = Column(Integer, index=True)
    extra = Column(JSON)

    source_id = Column(Integer, ForeignKey("data_sources.id"), nullable=True, index=True)
    data_source = relationship("DataSource", back_populates="prospects")

    inferred_data = relationship(
        "InferredProspectData",
        back_populates="prospect",
        uselist=False,
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<Prospect(id='{self.id}', source_id='{self.source_id}', title='{self.title[:30] if self.title else ''}...')>"

    def to_dict(self):
        import math

        def clean_value(v):
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
            "ai_enhanced_title": self.ai_enhanced_title,
            "description": self.description,
            "agency": self.agency,
            "naics": self.naics,
            "naics_description": self.naics_description,
            "naics_source": self.naics_source,
            "estimated_value": str(self.estimated_value) if self.estimated_value is not None else None,
            "est_value_unit": self.est_value_unit,
            "estimated_value_text": self.estimated_value_text,
            "estimated_value_min": str(self.estimated_value_min) if self.estimated_value_min is not None else None,
            "estimated_value_max": str(self.estimated_value_max) if self.estimated_value_max is not None else None,
            "estimated_value_single": str(self.estimated_value_single) if self.estimated_value_single is not None else None,
            "release_date": self.release_date.strftime("%Y-%m-%d") if self.release_date else None,
            "award_date": self.award_date.strftime("%Y-%m-%d") if self.award_date else None,
            "award_fiscal_year": self.award_fiscal_year,
            "place_city": self.place_city,
            "place_state": self.place_state,
            "place_country": self.place_country,
            "contract_type": self.contract_type,
            "set_aside": self.set_aside,
            "set_aside_standardized": self.set_aside_standardized,
            "set_aside_standardized_label": self.set_aside_standardized_label,
            "primary_contact_email": self.primary_contact_email,
            "primary_contact_name": self.primary_contact_name,
            "loaded_at": self.loaded_at.isoformat() + "Z" if self.loaded_at else None,
            "ollama_processed_at": self.ollama_processed_at.replace(tzinfo=UTC).isoformat().replace("+00:00", "Z") if self.ollama_processed_at else None,
            "ollama_model_version": self.ollama_model_version,
            "enhancement_status": self.enhancement_status,
            "enhancement_started_at": self.enhancement_started_at.isoformat() + "Z" if self.enhancement_started_at else None,
            "enhancement_user_id": self.enhancement_user_id,
            "extra": clean_value(self.extra) if self.extra else None,
            "source_id": self.source_id,
            "source_name": self.data_source.name if self.data_source else None,
        }


class DataSource(db.Model):
    __tablename__ = "data_sources"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False, unique=True, index=True)
    url = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    scraper_key = Column(String, nullable=True, index=True)
    last_scraped = Column(TIMESTAMP(timezone=True), nullable=True)
    frequency = Column(String, nullable=True)

    status_records = relationship("ScraperStatus", back_populates="data_source", cascade="all, delete-orphan")
    prospects = relationship("Prospect", back_populates="data_source")

    def __repr__(self):
        return f"<DataSource(id={self.id}, name='{self.name}')>"

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "url": self.url,
            "description": self.description,
            "scraper_key": self.scraper_key,
            "last_scraped": self.last_scraped.isoformat() + "Z" if self.last_scraped else None,
            "frequency": self.frequency,
        }


class ScraperStatus(db.Model):
    __tablename__ = "scraper_status"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_id = Column(Integer, ForeignKey("data_sources.id"), nullable=False, index=True)
    status = Column(String, nullable=True)
    last_checked = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    details = Column(Text, nullable=True)

    data_source = relationship("DataSource", back_populates="status_records")

    def __repr__(self):
        return f"<ScraperStatus(id={self.id}, source_id={self.source_id}, status='{self.status}')>"

    def to_dict(self):
        return {
            "id": self.id,
            "source_id": self.source_id,
            "status": self.status,
            "last_checked": self.last_checked.isoformat() + "Z" if self.last_checked else None,
            "details": self.details,
        }


class AIEnrichmentLog(db.Model):
    __tablename__ = "ai_enrichment_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), index=True)
    enhancement_type = Column(String(50), nullable=False, index=True)
    status = Column(String(20), nullable=False, index=True)
    processed_count = Column(Integer, nullable=False, default=0)
    duration = Column(Float, nullable=True)
    message = Column(Text, nullable=True)
    error = Column(Text, nullable=True)

    def __repr__(self):
        return f"<AIEnrichmentLog(id={self.id}, enhancement_type='{self.enhancement_type}', status='{self.status}', processed_count={self.processed_count})>"

    def to_dict(self):
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat() + "Z" if self.timestamp else None,
            "enhancement_type": self.enhancement_type,
            "status": self.status,
            "processed_count": self.processed_count,
            "duration": self.duration,
            "message": self.message,
            "error": self.error,
        }


class LLMOutput(db.Model):
    __tablename__ = "llm_outputs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), index=True)
    prospect_id = Column(String, ForeignKey("prospects.id"), nullable=True, index=True)
    enhancement_type = Column(String(50), nullable=False, index=True)
    prompt = Column(Text, nullable=True)
    response = Column(Text, nullable=True)
    parsed_result = Column(JSON, nullable=True)
    success = Column(db.Boolean, default=True)
    error_message = Column(Text, nullable=True)
    processing_time = Column(Float, nullable=True)

    prospect = relationship("Prospect", backref="llm_outputs")

    def __repr__(self):
        return f"<LLMOutput(id={self.id}, prospect_id='{self.prospect_id}', enhancement_type='{self.enhancement_type}')>"

    def to_dict(self):
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat() + "Z" if self.timestamp else None,
            "prospect_id": self.prospect_id,
            "prospect_title": self.prospect.title[:100] if self.prospect and self.prospect.title else None,
            "enhancement_type": self.enhancement_type,
            "prompt": self.prompt[:200] + "..." if self.prompt and len(self.prompt) > 200 else self.prompt,
            "response": self.response,
            "parsed_result": self.parsed_result,
            "success": self.success,
            "error_message": self.error_message,
            "processing_time": self.processing_time,
        }


class Settings(db.Model):
    __tablename__ = "settings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(100), nullable=False, unique=True, index=True)
    value = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<Settings(key='{self.key}', value='{self.value}')>"

    def to_dict(self):
        return {
            "id": self.id,
            "key": self.key,
            "value": self.value,
            "description": self.description,
            "updated_at": self.updated_at.isoformat() + "Z" if self.updated_at else None,
        }


class GoNoGoDecision(db.Model):
    __tablename__ = "go_no_go_decisions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    prospect_id = Column(String, ForeignKey("prospects.id"), nullable=False, index=True)
    user_id = Column(Integer, nullable=False, index=True)  # No FK since user is in separate DB
    decision = Column(String(10), nullable=False, index=True)  # 'go' or 'no-go'
    reason = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    prospect = relationship("Prospect", backref="go_no_go_decisions")

    def __repr__(self):
        return f"<GoNoGoDecision(id={self.id}, prospect_id='{self.prospect_id}', user_id={self.user_id}, decision='{self.decision}')>"

    def to_dict(self, include_user=False, user_data=None):
        result = {
            "id": self.id,
            "prospect_id": self.prospect_id,
            "user_id": self.user_id,
            "decision": self.decision,
            "reason": self.reason,
            "created_at": self.created_at.isoformat() + "Z" if self.created_at else None,
            "updated_at": self.updated_at.isoformat() + "Z" if self.updated_at else None,
        }

        if include_user and user_data:
            result["user"] = user_data

        return result


class FileProcessingLog(db.Model):
    """Track file processing success for intelligent data retention."""

    __tablename__ = "file_processing_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_id = Column(Integer, ForeignKey("data_sources.id"), nullable=False, index=True)
    file_path = Column(String(500), nullable=False, index=True)
    file_name = Column(String(255), nullable=False, index=True)
    file_size = Column(Integer, nullable=True)
    file_timestamp = Column(TIMESTAMP(timezone=True), nullable=False, index=True)
    processing_started_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), index=True)
    processing_completed_at = Column(TIMESTAMP(timezone=True), nullable=True, index=True)
    success = Column(db.Boolean, nullable=False, default=False, index=True)
    records_extracted = Column(Integer, nullable=True)
    records_inserted = Column(Integer, nullable=True)
    schema_columns = Column(JSON, nullable=True)
    schema_issues = Column(JSON, nullable=True)
    validation_warnings = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    processing_duration = Column(Float, nullable=True)

    data_source = relationship("DataSource", backref="file_processing_logs")

    def __repr__(self):
        return f"<FileProcessingLog(id={self.id}, file_name='{self.file_name}', success={self.success})>"

    def to_dict(self):
        return {
            "id": self.id,
            "source_id": self.source_id,
            "source_name": self.data_source.name if self.data_source else None,
            "file_path": self.file_path,
            "file_name": self.file_name,
            "file_size": self.file_size,
            "file_timestamp": self.file_timestamp.isoformat() + "Z" if self.file_timestamp else None,
            "processing_started_at": self.processing_started_at.isoformat() + "Z" if self.processing_started_at else None,
            "processing_completed_at": self.processing_completed_at.isoformat() + "Z" if self.processing_completed_at else None,
            "success": self.success,
            "records_extracted": self.records_extracted,
            "records_inserted": self.records_inserted,
            "schema_columns": self.schema_columns,
            "schema_issues": self.schema_issues,
            "validation_warnings": self.validation_warnings,
            "error_message": self.error_message,
            "processing_duration": self.processing_duration,
        }


class InferredProspectData(db.Model):
    __tablename__ = "inferred_prospect_data"

    prospect_id = Column(String, ForeignKey("prospects.id"), primary_key=True)
    inferred_requirement_title = Column(Text, nullable=True)
    inferred_requirement_description = Column(Text, nullable=True)
    inferred_naics = Column(String, nullable=True)
    inferred_naics_description = Column(String(200), nullable=True)
    inferred_estimated_value = Column(Float, nullable=True)
    inferred_est_value_unit = Column(String, nullable=True)
    inferred_estimated_value_min = Column(Float, nullable=True)
    inferred_estimated_value_max = Column(Float, nullable=True)
    inferred_solicitation_date = Column(Text, nullable=True)
    inferred_award_date = Column(Text, nullable=True)
    inferred_place_city = Column(Text, nullable=True)
    inferred_place_state = Column(Text, nullable=True)
    inferred_place_country = Column(Text, nullable=True)
    inferred_contract_type = Column(Text, nullable=True)
    inferred_set_aside = Column(Text, nullable=True)
    inferred_primary_contact_email = Column(String(100), nullable=True)
    inferred_primary_contact_name = Column(String(100), nullable=True)
    llm_confidence_scores = Column(JSON, nullable=True)
    inferred_at = Column(TIMESTAMP(timezone=False), server_default=func.now(), onupdate=func.now())
    inferred_by_model = Column(String, nullable=True)

    prospect = relationship("Prospect", back_populates="inferred_data")

    def __repr__(self):
        return f"<InferredProspectData(prospect_id='{self.prospect_id}')>"


