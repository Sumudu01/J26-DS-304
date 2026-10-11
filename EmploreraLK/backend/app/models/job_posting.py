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
