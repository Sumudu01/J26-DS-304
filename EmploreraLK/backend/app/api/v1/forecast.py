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

logger = logging.getLogger("emploreralk.api.forecast")

router = APIRouter(prefix="/forecast", tags=["Forecasting & Data Collection"])


@router.post(
    "/jobs/collect",
    response_model=AgentRunStatus,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger Autonomous LinkedIn Data Collection Agent",
    description=(
        "Deploys the autonomous data collection agent to search, parse, "
        "deduplicate, and persist job posts from LinkedIn based on specified keywords and location."
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
    source: Optional[str] = Query(None, description="Filter by portal source: 'LinkedIn' or 'TopJobs'"),
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
