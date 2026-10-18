from app.core.database import Base
from app.models.user import User
from app.models.notification import Notification
from app.models.candidate_cv import CandidateCV
from app.models.job_posting import JobPosting, DataCollectionRun, NLPExtractionRun, SkillProcessingRun
from app.components.skill_gap.models import CandidateProfile, CandidateCollectionRun

<<<<<<< HEAD
__all__ = ["Base", "User", "Notification", "CandidateCV", "JobPosting", "DataCollectionRun", "NLPExtractionRun", "SkillProcessingRun"]
=======
__all__ = ["Base", "User", "Notification", "JobPosting", "DataCollectionRun", "NLPExtractionRun", "SkillProcessingRun", "CandidateProfile", "CandidateCollectionRun"]
>>>>>>> 2bb28ee60332b4cf74f61a35e20a8aed89379cd4
