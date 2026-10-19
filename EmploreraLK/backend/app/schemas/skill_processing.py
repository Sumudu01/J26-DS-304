from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class NormalizedSkillItem(BaseModel):
    """Normalized skill with canonical representation, taxonomy placement, and weights."""
    canonical_name: str
    original_mention: str
    domain: str = "General IT"
    category: str = "General"
    subcategory: Optional[str] = None
    weight: float = 1.0
    is_core: bool = False
    implied_skills: List[str] = Field(default_factory=list)
    match_method: str = "exact_canonical"  # exact_canonical, alias_mapping, fuzzy_match, implied
    confidence: float = 1.0


class JobSkillProcessingResult(BaseModel):
    """Detailed result of processing skills for a single job posting."""
    job_id: str
    title: str
    company: str
    raw_skills: List[str]
    canonical_skills: List[str]
    normalized_skills: List[NormalizedSkillItem]
    skills_by_domain: Dict[str, List[str]]
    skills_by_category: Dict[str, List[str]]
    implied_skills: List[str]
    core_skills: List[str]
    total_skills_count: int
    processing_confidence: float = 1.0


class SkillProcessingGoal(BaseModel):
    """Goal configuration defining autonomous skill processing batch execution."""
    batch_size: int = Field(
        default=50,
        ge=1,
        le=500,
        description="Maximum number of job postings to process in this run"
    )
    force_reprocess: bool = Field(
        default=False,
        description="Whether to re-process jobs that were already marked as processed"
    )
    source: Optional[str] = Field(
        default=None,
        description="Optional platform filter: 'LinkedIn', 'TopJobs', 'Rooster.jobs', or None for all"
    )
    fuzzy_threshold: float = Field(
        default=0.85,
        ge=0.5,
        le=1.0,
        description="Fuzzy similarity threshold for typo-tolerant skill normalization"
    )
    enable_implication: bool = Field(
        default=True,
        description="Whether to automate ontological implication deduction (e.g. FastAPI -> Python)"
    )
    background: bool = Field(
        default=False,
        description="Run processing asynchronously in a background worker thread"
    )


class SkillProcessingRunStatus(BaseModel):
    """Status report and telemetry of a Skill Processing Agent execution."""
    run_id: str
    status: str
    total_processed: int
    skills_normalized_count: int
    unique_canonical_skills_count: int
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    top_canonical_skills: Optional[List[Dict[str, Any]]] = None
    domain_distribution: Optional[Dict[str, int]] = None
    execution_summary: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class AdHocSkillNormalizationRequest(BaseModel):
    """Ad-hoc request to normalize an arbitrary list of raw skill strings."""
    skills: List[str] = Field(..., min_length=1, description="List of raw skill strings to normalize")
    job_title: Optional[str] = Field(default="", description="Optional job title for importance & core skill weighting")
    fuzzy_threshold: float = Field(default=0.85, ge=0.5, le=1.0, description="Fuzzy match threshold")
    enable_implication: bool = Field(default=True, description="Enable ontological skill implication deduction")


class AdHocSkillNormalizationResponse(BaseModel):
    """Response containing normalized, categorized, and deduplicated skills."""
    normalized_skills: List[NormalizedSkillItem]
    canonical_skills: List[str]
    implied_skills: List[str]
    core_skills: List[str]
    domain_breakdown: Dict[str, List[str]]
    category_breakdown: Dict[str, List[str]]
    total_canonical_count: int


class SkillCoOccurrenceItem(BaseModel):
    skill: str
    co_occurrence_count: int
    strength: float


class SkillCoOccurrenceResponse(BaseModel):
    target_skill: str
    canonical_name: str
    total_postings_with_skill: int
    co_occurring_skills: List[SkillCoOccurrenceItem]


class TaxonomyTreeResponse(BaseModel):
    total_domains: int
    total_categories: int
    total_canonical_skills: int
    tree: Dict[str, Any]
