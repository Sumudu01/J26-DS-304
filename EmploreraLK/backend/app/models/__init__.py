from app.core.database import Base
from app.models.user import User
from app.models.notification import Notification
from app.models.candidate_cv import CandidateCV
from app.models.job_posting import JobPosting, DataCollectionRun, NLPExtractionRun, SkillProcessingRun
from app.models.forecast_run import ForecastRun
from app.components.skill_gap.models import CandidateProfile, CandidateCollectionRun

__all__ = ["Base", "User", "Notification", "CandidateCV", "JobPosting", "DataCollectionRun", "NLPExtractionRun", "SkillProcessingRun", "ForecastRun", "CandidateProfile", "CandidateCollectionRun"]
