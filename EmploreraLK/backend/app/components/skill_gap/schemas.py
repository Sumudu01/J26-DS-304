from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class SkillGapAnalysisRequest(BaseModel):
    skills: List[str] = Field(default_factory=list, max_length=100)
    target_role: str = Field(min_length=1, max_length=255)


class SkillGapAnalysisResponse(BaseModel):
    target_role: str
    match_percentage: int
    matching_skills: List[str]
    missing_skills: List[str]
    target_skills: List[str]
    graph_data: dict[str, Any]
    skill_roadmap: List[dict[str, Any]]


class CandidateCollectionRequest(BaseModel):
    profile_urls: List[str] = Field(min_length=1, max_length=50)


class CandidateProfileResponse(BaseModel):
    id: int
    source_url: str
    source: str
    full_name: Optional[str] = None
    headline: Optional[str] = None
    location: Optional[str] = None
    bio: Optional[str] = None
    skills: List[str] = Field(default_factory=list)
    projects: List[dict[str, Any]] = Field(default_factory=list)
    raw_data: dict[str, Any] = Field(default_factory=dict)
    collected_at: datetime


class CandidateCollectionResult(BaseModel):
    source_url: str
    status: str
    message: Optional[str] = None
    candidate: Optional[CandidateProfileResponse] = None


class CandidateCollectionRunResponse(BaseModel):
    run_id: str
    status: str
    requested_count: int
    collected_count: int
    failed_count: int
    results: List[CandidateCollectionResult] = Field(default_factory=list)
    created_at: datetime
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class CandidateListResponse(BaseModel):
    total: int
    items: List[CandidateProfileResponse]