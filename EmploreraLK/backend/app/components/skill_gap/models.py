import json

from sqlalchemy import Column, DateTime, Integer, String, Text, inspect, text
from sqlalchemy.sql import func

from app.core.database import Base


class CandidateProfile(Base):
    __tablename__ = "candidate_profiles"

    id = Column(Integer, primary_key=True, index=True)
    owner_user_id = Column(Integer, nullable=False, index=True)
    source_url = Column(String(1024), unique=True, nullable=False, index=True)
    source = Column(String(50), nullable=False, index=True)
    full_name = Column(String(255), nullable=True, index=True)
    headline = Column(String(512), nullable=True)
    location = Column(String(255), nullable=True)
    bio = Column(Text, nullable=True)
    skills_json = Column(Text, nullable=False, default="[]")
    projects_json = Column(Text, nullable=False, default="[]")
    raw_json = Column(Text, nullable=False, default="{}")
    collected_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "source_url": self.source_url,
            "source": self.source,
            "full_name": self.full_name,
            "headline": self.headline,
            "location": self.location,
            "bio": self.bio,
            "skills": json.loads(self.skills_json or "[]"),
            "projects": json.loads(self.projects_json or "[]"),
            "raw_data": json.loads(self.raw_json or "{}"),
            "collected_at": self.collected_at,
        }


class CandidateCollectionRun(Base):
    __tablename__ = "candidate_collection_runs"

    id = Column(Integer, primary_key=True, index=True)
    owner_user_id = Column(Integer, nullable=False, index=True)
    run_id = Column(String(64), unique=True, nullable=False, index=True)
    status = Column(String(32), nullable=False, default="queued", index=True)
    requested_count = Column(Integer, nullable=False, default=0)
    collected_count = Column(Integer, nullable=False, default=0)
    failed_count = Column(Integer, nullable=False, default=0)
    results_json = Column(Text, nullable=False, default="[]")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    def get_results(self):
        try:
            results = json.loads(self.results_json or "[]")
            return results if isinstance(results, list) else []
        except (TypeError, ValueError):
            return []


def ensure_candidate_ownership_columns(bind) -> None:
    """Upgrade candidate tables created before profile ownership was introduced."""
    inspector = inspect(bind)
    existing_tables = set(inspector.get_table_names())
    for table_name in ("candidate_profiles", "candidate_collection_runs"):
        if table_name not in existing_tables:
            continue
        columns = {column["name"] for column in inspector.get_columns(table_name)}
        if "owner_user_id" in columns:
            continue
        with bind.begin() as connection:
            connection.execute(text(f'ALTER TABLE "{table_name}" ADD COLUMN owner_user_id INTEGER'))
            connection.execute(text(
                f'CREATE INDEX IF NOT EXISTS "ix_{table_name}_owner_user_id" '
                f'ON "{table_name}" (owner_user_id)'
            ))