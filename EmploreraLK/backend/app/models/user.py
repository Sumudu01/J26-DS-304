import json
from datetime import datetime, timezone
from typing import List
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime
from sqlalchemy.sql import func
from app.core.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=True)  # nullable for OAuth-only accounts
    name = Column(String(255), nullable=False)
    role = Column(String(50), default="seeker", nullable=False)  # 'seeker', 'recruiter', 'admin'

    # OAuth fields
    google_id = Column(String(255), unique=True, nullable=True, index=True)
    linkedin_id = Column(String(255), unique=True, nullable=True, index=True)
    avatar_url = Column(String(512), nullable=True)

    # Seeker specific fields
    current_role = Column(String(255), nullable=True)
    target_role = Column(String(255), nullable=True)
    skills = Column(Text, nullable=True)  # JSON-encoded list or comma-separated string

    # Recruiter specific fields
    company = Column(String(255), nullable=True)

    # Account status
    is_active = Column(Boolean, default=True, nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def get_skills_list(self) -> List[str]:
        """Convert skills column to list of strings."""
        if not self.skills:
            return []
        try:
            parsed = json.loads(self.skills)
            if isinstance(parsed, list):
                return [str(s).strip() for s in parsed if str(s).strip()]
        except Exception:
            pass
        return [s.strip() for s in self.skills.split(",") if s.strip()]

    def set_skills_list(self, skills_input) -> None:
        """Store skills as a JSON array string."""
        if isinstance(skills_input, list):
            clean_list = [str(s).strip() for s in skills_input if str(s).strip()]
        elif isinstance(skills_input, str):
            clean_list = [s.strip() for s in skills_input.split(",") if s.strip()]
        else:
            clean_list = []
        self.skills = json.dumps(clean_list)

