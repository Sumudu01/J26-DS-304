import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.job_posting import (
    AgentCollectionGoal,
    AgentRunStatus,
    JobListResponse,
)
from app.components.forecasting.services.scraping_service import ScrapingService
from app.components.forecasting.services.forecasting_service import ForecastingService
from app.components.forecasting.agents.job_posting_time_series_agent import (
    JobPostingTimeSeriesAgent,
    TimeSeriesInterval,
)

logger = logging.getLogger("emploreralk.api.forecast")

router = APIRouter(prefix="/forecast", tags=["Forecasting & Data Collection"])


@router.post(
    "/jobs/collect",
    response_model=AgentRunStatus,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger Autonomous Job Data Collection Agent",
    description=(
        "Deploys the autonomous data collection agent to search, parse, "
        "deduplicate, and persist job posts from LinkedIn, TopJobs, and Rooster.jobs. After collection, "
        "job descriptions and skills are extracted and saved; TopJobs advert images are OCRed."
    )
)
def trigger_data_collection(
    goal: AgentCollectionGoal,
    db: Session = Depends(get_db)
) -> AgentRunStatus:
    try:
        run_status = ScrapingService.trigger_collection(goal=goal, db=db)
        return run_status
    except Exception as e:
        logger.error("Error launching data collection agent: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Agent deployment failed: {str(e)}"
        )


@router.get(
    "/agent/runs/{run_id}",
    response_model=AgentRunStatus,
    summary="Check Agent Run Status & Telemetry",
    description="Retrieve execution state, telemetry logs, and collected counts for a specific agent run."
)
def get_agent_run_status(
    run_id: str,
    db: Session = Depends(get_db)
) -> AgentRunStatus:
    status_info = ScrapingService.get_run_status(run_id=run_id, db=db)
    if not status_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent run '{run_id}' not found."
        )
    return status_info


@router.get(
    "/agent/runs",
    response_model=List[AgentRunStatus],
    summary="List Recent Agent Collection Runs",
    description="Retrieve the history of autonomous data collection runs."
)
def list_agent_runs(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
) -> List[AgentRunStatus]:
    return ScrapingService.get_all_runs(db=db, limit=limit)


@router.get(
    "/jobs",
    response_model=JobListResponse,
    summary="Query Scraped Job Postings",
    description="Search and filter collected job postings with pagination."
)
def list_collected_jobs(
    keyword: Optional[str] = Query(None, description="Search keyword in title, tag, or description"),
    location: Optional[str] = Query(None, description="Filter by location"),
    company: Optional[str] = Query(None, description="Filter by company name"),
    source: Optional[str] = Query(None, description="Filter by portal source: 'LinkedIn', 'TopJobs', or 'Rooster.jobs'"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(25, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db)
) -> JobListResponse:
    return ScrapingService.list_jobs(
        db=db,
        keyword=keyword,
        location=location,
        company=company,
        source=source,
        page=page,
        page_size=page_size
    )



@router.get(
    "/jobs/stats",
    response_model=Dict[str, Any],
    summary="Data Collection Statistics",
    description="Aggregated metrics of collected job posts for the demand forecasting pipeline."
)
def get_collection_stats(
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    return ScrapingService.get_collection_statistics(db=db)


@router.get(
    "/jobs/time-series",
    response_model=Dict[str, Any],
    summary="Get job-posting and skill time series",
    description=(
        "Aggregate dated job postings and extracted skills over up to 730 days. "
        "Includes the newest and older postings available in the database."
    ),
)
def get_job_posting_time_series(
    days: int = Query(730, ge=1, le=730),
    interval: TimeSeriesInterval = Query("month"),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    return JobPostingTimeSeriesAgent.get_series(db, days=days, interval=interval)


@router.get(
    "/demand-insights",
    response_model=Dict[str, Any],
    summary="Forecast emerging and declining job-market skills",
    description=(
        "Compares extracted skills in the latest 12 months of dated job postings "
        "with the preceding 12 months and generates an explainable target-year outlook."
    ),
)
def get_demand_insights(
    target_year: int = Query(2029, ge=2027, le=2036),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    return ForecastingService.get_demand_insights(db=db, target_year=target_year)


@router.get(
    "/demand-forecast",
    response_model=Dict[str, Any],
    summary="Get the latest persisted multi-model job-market forecast",
    description="Return model evaluations and monthly emerging/declining skill and role forecasts for up to 36 months.",
)
def get_demand_forecast(
    horizon_months: int = Query(36, ge=1, le=36),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    result = ForecastingService.get_latest_forecast(
        db,
        horizon_months=horizon_months,
    )
    return result or {
        "available": False,
        "message": "No model forecast is stored yet. Start a forecast run to train the models.",
    }


@router.post(
    "/demand-forecast/train",
    response_model=Dict[str, Any],
    summary="Train, evaluate, and persist demand forecasting models",
    description="Evaluate ARIMA, Prophet, N-BEATS, and TFT on a temporal holdout, then select the best model per skill and role.",
)
def train_demand_forecast(
    horizon_months: int = Query(36, ge=1, le=36),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    try:
        ForecastingService.train_and_store(
            db,
            horizon_months=36,
        )
        result = ForecastingService.get_latest_forecast(
            db,
            horizon_months=horizon_months,
        )
        if result is None:
            raise RuntimeError("Forecast training completed without a saved result")
        return result
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except RuntimeError as exc:
        logger.error("No demand forecasting model could be trained: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        db.rollback()
        logger.exception("Demand forecasting run failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Demand forecasting failed. See backend logs for details.",
        ) from exc


@router.get(
    "/demand-forecast/history",
    response_model=List[Dict[str, Any]],
    summary="Browse stored forecast knowledge",
    description="List previous persisted model evaluations and generated forecast insights.",
)
def get_demand_forecast_history(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    return ForecastingService.get_forecast_history(db, limit=limit)


# ─── NLP Skill Extraction Agent Endpoints ────────────────────────────────────

from app.schemas.nlp_extraction import (
    NLPExtractionGoal,
    NLPExtractionRunStatus,
    TextSkillExtractionRequest,
    TextSkillExtractionResponse,
)
from app.components.forecasting.services.nlp_service import NLPService


@router.post(
    "/nlp/extract",
    response_model=NLPExtractionRunStatus,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger Autonomous NLP Skill Extraction Agent",
    description="Deploys the NLP Extraction Agent to parse technical skills, soft skills, seniority, experience, and education from collected job postings."
)
def trigger_nlp_extraction(
    goal: NLPExtractionGoal,
    db: Session = Depends(get_db)
) -> NLPExtractionRunStatus:
    try:
        return NLPService.trigger_extraction(goal=goal, db=db)
    except Exception as e:
        logger.error("Error launching NLP extraction agent: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"NLP extraction agent deployment failed: {str(e)}"
        )


@router.post(
    "/nlp/extract-text",
    response_model=TextSkillExtractionResponse,
    summary="Ad-hoc NLP Skill Extraction from Raw Text",
    description="Extract skills, seniority level, experience requirements, and education credentials from arbitrary job text or candidate profile."
)
def extract_skills_from_text(
    payload: TextSkillExtractionRequest
) -> TextSkillExtractionResponse:
    return NLPService.extract_from_raw_text(text=payload.text, title=payload.title)


@router.get(
    "/nlp/runs",
    response_model=List[NLPExtractionRunStatus],
    summary="List NLP Extraction Runs",
    description="Retrieve the history of autonomous NLP skill extraction runs."
)
def list_nlp_runs(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
) -> List[NLPExtractionRunStatus]:
    return NLPService.get_all_runs(db=db, limit=limit)


@router.get(
    "/nlp/runs/{run_id}",
    response_model=NLPExtractionRunStatus,
    summary="Check NLP Extraction Run Status",
    description="Retrieve status and top skills extracted during a specific agent execution."
)
def get_nlp_run_status(
    run_id: str,
    db: Session = Depends(get_db)
) -> NLPExtractionRunStatus:
    status_info = NLPService.get_run_status(run_id=run_id, db=db)
    if not status_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"NLP extraction run '{run_id}' not found."
        )
    return status_info


@router.get(
    "/nlp/skills/distribution",
    response_model=Dict[str, Any],
    summary="Global Extracted Skill Distribution",
    description="Aggregated frequencies of all skills extracted across collected job postings."
)
def get_skill_distribution(
    limit: int = Query(30, ge=1, le=100),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    return NLPService.get_global_skill_distribution(db=db, limit=limit)


# ─── Skill Processing & Normalization Agent Endpoints ────────────────────────

from app.schemas.skill_processing import (
    SkillProcessingGoal,
    SkillProcessingRunStatus,
    AdHocSkillNormalizationRequest,
    AdHocSkillNormalizationResponse,
    SkillCoOccurrenceResponse,
    TaxonomyTreeResponse,
)
from app.components.forecasting.services.skill_processing_service import SkillProcessingService


@router.post(
    "/skills/process",
    response_model=SkillProcessingRunStatus,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger Autonomous Skill Processing & Normalization Agent",
    description=(
        "Deploys the Skill Processing Agent to normalize raw skill mentions, resolve typos, "
        "apply title importance weighting, deduce ontological implications, and classify into multi-tier taxonomies."
    )
)
def trigger_skill_processing(
    goal: SkillProcessingGoal,
    db: Session = Depends(get_db)
) -> SkillProcessingRunStatus:
    try:
        return SkillProcessingService.trigger_processing(goal=goal, db=db)
    except Exception as e:
        logger.error("Error deploying Skill Processing Agent: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Skill processing agent deployment failed: {str(e)}"
        )


@router.post(
    "/skills/normalize",
    response_model=AdHocSkillNormalizationResponse,
    summary="Normalize Raw Skills Array (Ad-Hoc)",
    description=(
        "Normalizes an arbitrary list of skill strings into canonical representations with "
        "typo tolerance, hierarchical taxonomy placement, and optional ontological implication deduction."
    )
)
def normalize_skills_adhoc(
    payload: AdHocSkillNormalizationRequest
) -> AdHocSkillNormalizationResponse:
    try:
        return SkillProcessingService.normalize_adhoc_skills(payload=payload)
    except Exception as e:
        logger.error("Error normalizing skills: %s", e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Skill normalization failed: {str(e)}"
        )


@router.get(
    "/skills/runs",
    response_model=List[SkillProcessingRunStatus],
    summary="List Skill Processing Agent Runs",
    description="Retrieve the execution history of autonomous skill processing and normalization agent runs."
)
def list_skill_processing_runs(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
) -> List[SkillProcessingRunStatus]:
    return SkillProcessingService.get_all_runs(db=db, limit=limit)


@router.get(
    "/skills/runs/{run_id}",
    response_model=SkillProcessingRunStatus,
    summary="Get Skill Processing Run Status",
    description="Retrieve execution report, telemetry steps, and normalized skill metrics for a specific agent run."
)
def get_skill_processing_run_status(
    run_id: str,
    db: Session = Depends(get_db)
) -> SkillProcessingRunStatus:
    status_info = SkillProcessingService.get_run_status(run_id=run_id, db=db)
    if not status_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Skill processing run '{run_id}' not found."
        )
    return status_info


@router.get(
    "/skills/taxonomy",
    response_model=TaxonomyTreeResponse,
    summary="Hierarchical IT Skill Taxonomy Tree",
    description="Retrieve the complete multi-tier taxonomy tree across all domains, categories, canonical skills, and aliases."
)
def get_taxonomy_tree() -> TaxonomyTreeResponse:
    return SkillProcessingService.get_taxonomy_tree()


@router.get(
    "/skills/co-occurrences/{skill_name}",
    response_model=SkillCoOccurrenceResponse,
    summary="Skill Co-occurrence Network & Clusters",
    description="Discover the most frequently co-occurring skills and cluster relationships for a given target skill."
)
def get_skill_co_occurrences(
    skill_name: str,
    limit: int = Query(15, ge=1, le=50),
    db: Session = Depends(get_db)
) -> SkillCoOccurrenceResponse:
    return SkillProcessingService.get_skill_co_occurrences(
        skill_name=skill_name,
        db=db,
        limit=limit
    )


# ─── Personalized Recommended Jobs Endpoint ──────────────────────────────────

@router.get(
    "/jobs/recommended",
    response_model=Dict[str, Any],
    summary="Personalized Job Listings for User's Target Role",
    description=(
        "Returns real-time job postings from the database matched to the user's target role "
        "and skill profile. Jobs are scored by skill-overlap and sorted by relevance then recency. "
        "Sourced from LinkedIn, TopJobs, and Rooster.jobs via the autonomous pipeline."
    ),
)
def get_recommended_jobs(
    target_role: Optional[str] = Query(None, description="User's target job role (from profile)"),
    skills: Optional[str] = Query(None, description="Comma-separated user skills for overlap scoring"),
    keyword: Optional[str] = Query(None, description="Free-text job title or skill keyword"),
    source: Optional[str] = Query(None, description="Filter by source platform: LinkedIn, TopJobs, or Rooster.jobs"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=50, description="Results per page"),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    if not (target_role or (keyword and keyword.strip())):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide target_role or keyword to search job listings.",
        )
    try:
        user_skills = [s.strip() for s in skills.split(",") if s.strip()] if skills else []
        return ScrapingService.get_recommended_jobs(
            db=db,
            target_role=target_role,
            user_skills=user_skills,
            page=page,
            page_size=page_size,
            source_filter=source,
            keyword=keyword,
        )
    except Exception as e:
        logger.error("Error fetching recommended jobs: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch recommended jobs: {str(e)}"
        )


# ─── Full Agentic Pipeline Trigger ───────────────────────────────────────────

@router.post(
    "/pipeline/run",
    response_model=Dict[str, Any],
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger Full 4-Agent Pipeline for a Target Role",
    description=(
        "Orchestrates the complete autonomous pipeline: "
        "Data Collection Agent → NLP Extraction Agent → Skill Processing Agent → "
        "persists structured, normalized job postings ready for personalized display. "
        "Runs entirely in background. Returns a pipeline_id with per-stage status."
    ),
)
def trigger_full_pipeline(
    target_role: str = Query(..., description="Target role to collect and process jobs for"),
    location: str = Query("Sri Lanka", description="Geographic scope for job collection"),
    max_jobs: int = Query(25, ge=5, le=200, description="Max jobs to collect per platform (25 is fast, 50+ is thorough)"),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    try:
        return ScrapingService.trigger_full_pipeline(
            target_role=target_role,
            location=location,
            max_jobs=max_jobs,
            db=db,
        )
    except Exception as e:
        logger.error("Error triggering full pipeline: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Pipeline trigger failed: {str(e)}"
        )
