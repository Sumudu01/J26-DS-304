import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func
from app.core.database import Base


class JobPosting(Base):
    """
    SQLAlchemy Model representing raw job postings scraped from platforms like LinkedIn.
    Part of the EmploreraLK Job Market Demand Forecasting Engine data pipeline.
    """
    __tablename__ = "job_postings"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String(128), unique=True, index=True, nullable=False)
    title = Column(String(255), nullable=False, index=True)
    company = Column(String(255), nullable=False, index=True)
    location = Column(String(255), nullable=True, index=True)
    job_link = Column(Text, nullable=False)
    posted_date_text = Column(String(100), nullable=True)
    posted_timestamp = Column(DateTime(timezone=True), nullable=True, index=True)
    source = Column(String(50), default="LinkedIn", nullable=False, index=True)
    search_keyword = Column(String(255), nullable=True, index=True)
    status = Column(String(50), default="collected", nullable=False, index=True)  # collected, extracted, processed
    quality_score = Column(Integer, default=100)
    description_raw = Column(Text, nullable=True)
    raw_metadata = Column(Text, nullable=True)  # JSON-serialized metadata dictionary

    # NLP Extracted Attributes
    skills_extracted = Column(Text, nullable=True)  # JSON-serialized list of unique skills
    seniority_level = Column(String(50), nullable=True)  # Junior, Mid, Senior, Lead, etc.
    experience_years_min = Column(Integer, nullable=True)  # Minimum years of experience required
    education_level = Column(String(100), nullable=True)  # Bachelor's, Master's, etc.

    # Normalized & Processed Skill Attributes (Skill Processing Agent)
    skills_processed = Column(Text, nullable=True)  # JSON-serialized structured skill metadata & hierarchy
    processed_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def get_metadata(self) -> Dict[str, Any]:
        """Safely deserialize metadata JSON."""
        if not self.raw_metadata:
            return {}
        try:
            return json.loads(self.raw_metadata)
        except Exception:
            return {}

    def set_metadata(self, data: Dict[str, Any]) -> None:
        """Serialize metadata dictionary to JSON."""
        self.raw_metadata = json.dumps(data)

    @property
    def source_platforms(self) -> list:
        """Return distinct source portals represented by this canonical posting."""
        metadata_sources = self.get_metadata().get("source_platforms", [])
        if not isinstance(metadata_sources, list):
            metadata_sources = []
        return list(dict.fromkeys(
            [str(source) for source in metadata_sources if source]
            + ([self.source] if self.source else [])
        ))

    @property
    def source_jobs(self) -> list:
        """Return the source-specific links merged into this posting."""
        references = self.get_metadata().get("source_jobs", [])
        if isinstance(references, list):
            references = [
                reference for reference in references
                if isinstance(reference, dict)
                and reference.get("source")
                and reference.get("job_link")
            ]
        else:
            references = []
        if references:
            return references
        return [{
            "source": self.source,
            "job_id": self.job_id,
            "job_link": self.job_link,
        }]

    def get_skills(self) -> list:
        """Get parsed list of extracted skills."""
        if not self.skills_extracted:
            return []
        try:
            parsed = json.loads(self.skills_extracted)
            if isinstance(parsed, list):
                return parsed
        except Exception:
            pass
        return [s.strip() for s in self.skills_extracted.split(",") if s.strip()]

    def set_skills(self, skills_list: list) -> None:
        """Store unique skills as JSON list."""
        if isinstance(skills_list, (list, set)):
            clean = sorted(list({str(s).strip() for s in skills_list if str(s).strip()}))
            self.skills_extracted = json.dumps(clean)
        else:
            self.skills_extracted = json.dumps([])

    def get_processed_skills(self) -> Dict[str, Any]:
        """Safely deserialize normalized skills metadata dictionary."""
        if not self.skills_processed:
            return {}
        try:
            parsed = json.loads(self.skills_processed)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            pass
        return {}

    def set_processed_skills(self, data: Dict[str, Any]) -> None:
        """Serialize normalized skills metadata dictionary."""
        if isinstance(data, dict):
            self.skills_processed = json.dumps(data)
        else:
            self.skills_processed = json.dumps({})



class DataCollectionRun(Base):
    """
    SQLAlchemy Model tracking autonomous agent data collection runs,
    telemetry, status, and execution metrics.
    """
    __tablename__ = "data_collection_runs"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(String(64), unique=True, index=True, nullable=False)
    source = Column(String(50), default="LinkedIn", nullable=False)
    target_keywords = Column(String(255), nullable=False)
    target_location = Column(String(255), nullable=False)
    target_count = Column(Integer, default=100)
    collected_count = Column(Integer, default=0)
    duplicate_count = Column(Integer, default=0)
    status = Column(String(50), default="pending", nullable=False)  # pending, running, completed, failed, rate_limited
    execution_summary = Column(Text, nullable=True)  # JSON-serialized telemetry & metrics
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    def get_summary(self) -> Dict[str, Any]:
        if not self.execution_summary:
            return {}
        try:
            return json.loads(self.execution_summary)
        except Exception:
            return {}

    def set_summary(self, data: Dict[str, Any]) -> None:
        self.execution_summary = json.dumps(data)


class NLPExtractionRun(Base):
    """
    SQLAlchemy Model tracking autonomous NLP skill extraction runs,
    telemetry, and performance metrics.
    """
    __tablename__ = "nlp_extraction_runs"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(String(64), unique=True, index=True, nullable=False)
    total_processed = Column(Integer, default=0)
    skills_extracted_count = Column(Integer, default=0)
    status = Column(String(50), default="completed", nullable=False)  # running, completed, failed
    execution_summary = Column(Text, nullable=True)  # JSON-serialized telemetry
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    def get_summary(self) -> Dict[str, Any]:
        if not self.execution_summary:
            return {}
        try:
            return json.loads(self.execution_summary)
        except Exception:
            return {}

    def set_summary(self, data: Dict[str, Any]) -> None:
        self.execution_summary = json.dumps(data)


class SkillProcessingRun(Base):
    """
    SQLAlchemy Model tracking autonomous Skill Processing Agent runs,
    telemetry, normalization metrics, and taxonomy coverage.
    """
    __tablename__ = "skill_processing_runs"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(String(64), unique=True, index=True, nullable=False)
    total_processed = Column(Integer, default=0)
    skills_normalized_count = Column(Integer, default=0)
    unique_canonical_skills_count = Column(Integer, default=0)
    status = Column(String(50), default="completed", nullable=False)  # pending, running, completed, failed
    execution_summary = Column(Text, nullable=True)  # JSON-serialized telemetry & metrics
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    def get_summary(self) -> Dict[str, Any]:
        if not self.execution_summary:
            return {}
        try:
            return json.loads(self.execution_summary)
        except Exception:
            return {}

    def set_summary(self, data: Dict[str, Any]) -> None:
        self.execution_summary = json.dumps(data)
