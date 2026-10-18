"""Persisted candidate CV metadata and parsed representation."""

import json
from datetime import datetime
from typing import Any, Dict

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.sql import func

from app.core.database import Base


class CandidateCV(Base):
    __tablename__ = "candidate_cvs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    storage_key = Column(String(512), nullable=False, unique=True)
    original_filename = Column(String(255), nullable=False)
    content_type = Column(String(120), nullable=False)
    size_bytes = Column(Integer, nullable=False)
    sha256 = Column(String(64), nullable=False)
    parsed_data = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def get_parsed_data(self) -> Dict[str, Any]:
        try:
            value = json.loads(self.parsed_data)
        except (TypeError, ValueError):
            return {}
        return value if isinstance(value, dict) else {}

    def set_parsed_data(self, data: Dict[str, Any]) -> None:
        self.parsed_data = json.dumps(data)
