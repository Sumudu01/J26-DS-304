from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class ExtractedSkillItem(BaseModel):
    name: str
    category: str
    confidence: float = 1.0
    count: int = 1


class JobNLPExtractionResult(BaseModel):
    job_id: str
    title: str
    company: str
    skills: List[str]
    skills_by_category: Dict[str, List[str]]
    seniority_level: Optional[str] = None
    experience_years_min: Optional[int] = None
    education_level: Optional[str] = None
    extraction_confidence: float = 1.0


class NLPExtractionGoal(BaseModel):
    batch_size: int = Field(
        default=50,
        ge=1,
        le=500,
        description="Maximum number of job postings to process in this run"
    )
    force_reextract: bool = Field(
        default=False,
        description="Whether to re-extract skills from jobs that were already processed"
    )
    source: Optional[str] = Field(
        default=None,
        description="Optional platform filter: 'LinkedIn', 'TopJobs', 'Rooster.jobs', or None for all"
    )
    min_confidence: float = Field(
        default=0.7,
        ge=0.1,
        le=1.0,
        description="Minimum confidence score threshold"
    )
    background: bool = Field(
        default=False,
        description="Run extraction asynchronously in a background thread"
    )


class NLPExtractionRunStatus(BaseModel):
    run_id: str
    status: str
    total_processed: int
    skills_extracted_count: int
    unique_skills_count: int
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    top_skills: Optional[List[Dict[str, Any]]] = None
    execution_summary: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class TextSkillExtractionRequest(BaseModel):
    text: str = Field(..., description="Raw job description or vacancy text to parse")
    title: Optional[str] = Field(default="", description="Optional job title for contextual weighting")


class TextSkillExtractionResponse(BaseModel):
    skills: List[str]
    skills_by_category: Dict[str, List[str]]
    seniority_level: Optional[str] = None
    experience_years_min: Optional[int] = None
    education_level: Optional[str] = None
    confidence: float
