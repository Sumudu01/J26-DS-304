from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class JobPostingBase(BaseModel):
    job_id: str
    title: str
    company: str
    location: Optional[str] = None
    job_link: str
    posted_date_text: Optional[str] = None
    posted_timestamp: Optional[datetime] = None
    source: str = "LinkedIn"
    search_keyword: Optional[str] = None
    status: str = "collected"
    quality_score: Optional[int] = 100
    description_raw: Optional[str] = None


class JobPostingCreate(JobPostingBase):
    raw_metadata: Optional[str] = None


class JobPostingResponse(JobPostingBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AgentCollectionGoal(BaseModel):
    keywords: str = Field(
        default="Information Technology",
        description="Search keyword or role title to scrape"
    )
    location: str = Field(
        default="sri lanka",
        description="Geographic filter for job postings"
    )
    max_jobs: int = Field(
        default=50,
        ge=1,
        le=500,
        description="Target number of job postings to collect"
    )
    min_delay: float = Field(
        default=2.0,
        ge=0.5,
        description="Minimum polite delay between consecutive requests (seconds)"
    )
    max_delay: float = Field(
        default=4.0,
        ge=1.0,
        description="Maximum polite delay between consecutive requests (seconds)"
    )
    export_csv: bool = Field(
        default=False,
        description="Flag to also export collected jobs into local CSV file"
    )
    csv_filename: Optional[str] = Field(
        default=None,
        description="Custom CSV export filename"
    )
    background: bool = Field(
        default=True,
        description="Run agent asynchronously in the background"
    )


class AgentRunStatus(BaseModel):
    run_id: str
    source: str = "LinkedIn"
    status: str
    target_keywords: str
    target_location: str
    target_count: int
    collected_count: int
    duplicate_count: int
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    execution_summary: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class JobListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[JobPostingResponse]
