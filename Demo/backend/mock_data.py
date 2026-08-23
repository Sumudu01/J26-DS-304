# Mock data store for Emploeralk Prototype

DEFAULT_USERS = {
    "seeker@emploeralk.com": {
        "email": "seeker@emploeralk.com",
        "password": "password",
        "role": "seeker",
        "name": "Alex De Silva",
        "current_role": "Junior Python Developer",
        "skills": ["Python", "SQL", "Git", "HTML", "CSS"],
        "target_role": "AI Engineer"
    },
    "recruiter@emploeralk.com": {
        "email": "recruiter@emploeralk.com",
        "password": "password",
        "role": "recruiter",
        "name": "Jane Gamage",
        "company": "Axiata Labs"
    },
    "admin@emploeralk.com": {
        "email": "admin@emploeralk.com",
        "password": "password",
        "role": "admin",
        "name": "System Administrator"
    }
}

JOBS = [
    {
        "id": "job_001",
        "title": "AI Associate Engineer",
        "company": "WSO2",
        "platform": "LinkedIn",
        "location": "Colombo, Sri Lanka",
        "description": "We are seeking a junior AI Associate to help develop NLP models and deploy agents.",
        "required_skills": ["Python", "Machine Learning", "NLP", "Git", "API Development"],
        "salary": "LKR 180,000 - 250,000",
        "posted_date": "2026-08-20"
    },
    {
        "id": "job_002",
        "title": "Machine Learning Engineer",
        "company": "Dialog Axiata",
        "platform": "TopJobs.lk",
        "location": "Colombo 02, Sri Lanka",
        "description": "Looking for an ML engineer with strong focus on tabular data, PyTorch, and cloud deployment (AWS).",
        "required_skills": ["Python", "PyTorch", "AWS", "SQL", "Machine Learning", "Docker"],
        "salary": "LKR 300,000 - 450,000",
        "posted_date": "2026-08-18"
    },
    {
        "id": "job_003",
        "title": "Prompt Engineer & AI Consultant",
        "company": "Sysco LABS",
        "platform": "Indeed",
        "location": "Colombo, Sri Lanka (Hybrid)",
        "description": "Join our AI innovation hub to create, refine and evaluate LLM prompts and interface configurations.",
        "required_skills": ["Generative AI", "Python", "Prompt Engineering", "NLP", "Communication"],
        "salary": "LKR 280,000 - 380,000",
        "posted_date": "2026-08-22"
    },
    {
        "id": "job_004",
        "title": "Senior AI Architect",
        "company": "Virtusa",
        "platform": "LinkedIn",
        "location": "Colombo, Sri Lanka",
        "description": "Lead design and deployment of enterprise-grade AI applications using multi-agent frameworks.",
        "required_skills": ["Python", "Generative AI", "System Architecture", "Cloud Computing", "Team Leadership", "LangChain"],
        "salary": "LKR 600,000 - 800,000",
        "posted_date": "2026-08-15"
    },
    {
        "id": "job_005",
        "title": "Junior Software Engineer",
        "company": "Pearson",
        "platform": "Indeed",
        "location": "Colombo, Sri Lanka",
        "description": "Great entry-level position for software development in Python and JavaScript applications.",
        "required_skills": ["Python", "JavaScript", "SQL", "Git", "HTML"],
        "salary": "LKR 120,000 - 160,000",
        "posted_date": "2026-08-21"
    }
]

COURSES = [
    {
        "id": "course_001",
        "title": "Supervised Machine Learning: Regression and Classification",
        "provider": "Coursera (Stanford)",
        "skills_taught": ["Machine Learning", "Python", "Supervised Learning"],
        "duration": "3 weeks",
        "rating": 4.9,
        "link": "https://www.coursera.org/learn/machine-learning"
    },
    {
        "id": "course_002",
        "title": "Deep Learning Specialization",
        "provider": "Coursera (DeepLearning.AI)",
        "skills_taught": ["Machine Learning", "PyTorch", "NLP", "Deep Learning"],
        "duration": "12 weeks",
        "rating": 4.8,
        "link": "https://www.coursera.org/specializations/deep-learning"
    },
    {
        "id": "course_003",
        "title": "Generative AI with Large Language Models",
        "provider": "Coursera (AWS & DeepLearning.AI)",
        "skills_taught": ["Generative AI", "Prompt Engineering", "NLP", "Python"],
        "duration": "3 weeks",
        "rating": 4.7,
        "link": "https://www.coursera.org/learn/generative-ai-with-llms"
    },
    {
        "id": "course_004",
        "title": "AWS Cloud Practitioner Essentials",
        "provider": "Coursera (AWS)",
        "skills_taught": ["AWS", "Cloud Computing"],
        "duration": "2 weeks",
        "rating": 4.6,
        "link": "https://www.coursera.org/learn/aws-cloud-practitioner"
    },
    {
        "id": "course_005",
        "title": "API Development in Python with FastAPI",
        "provider": "Coursera (Build)",
        "skills_taught": ["Python", "API Development", "Git"],
        "duration": "4 weeks",
        "rating": 4.5,
        "link": "https://www.coursera.org/learn/fastapi-python"
    }
]

# Forecast data: Historical (2022-2025) and Projected/Forecasted (2026-2029)
SKILL_TRENDS = [
    {"year": 2022, "Generative AI": 10, "Python": 60, "Cloud Computing": 50, "Traditional Web": 75, "COBOL/Legacy": 30},
    {"year": 2023, "Generative AI": 35, "Python": 70, "Cloud Computing": 60, "Traditional Web": 72, "COBOL/Legacy": 25},
    {"year": 2024, "Generative AI": 65, "Python": 78, "Cloud Computing": 70, "Traditional Web": 68, "COBOL/Legacy": 20},
    {"year": 2025, "Generative AI": 88, "Python": 85, "Cloud Computing": 78, "Traditional Web": 65, "COBOL/Legacy": 15},
    {"year": 2026, "Generative AI": 100, "Python": 92, "Cloud Computing": 85, "Traditional Web": 60, "COBOL/Legacy": 12},  # Current
    {"year": 2027, "Generative AI": 115, "Python": 98, "Cloud Computing": 90, "Traditional Web": 55, "COBOL/Legacy": 10},  # Forecast
    {"year": 2028, "Generative AI": 130, "Python": 105, "Cloud Computing": 96, "Traditional Web": 50, "COBOL/Legacy": 8},  # Forecast
    {"year": 2029, "Generative AI": 140, "Python": 110, "Cloud Computing": 102, "Traditional Web": 45, "COBOL/Legacy": 5}   # Forecast
]

# Skill shortage data (Market Analysis for recruiter)
SKILL_DEMAND_VS_SUPPLY = [
    {"skill": "Generative AI", "demand": 95, "supply": 30, "gap": 65},
    {"skill": "Machine Learning", "demand": 88, "supply": 45, "gap": 43},
    {"skill": "AWS / Cloud Architecting", "demand": 80, "supply": 50, "gap": 30},
    {"skill": "Prompt Engineering", "demand": 75, "supply": 20, "gap": 55},
    {"skill": "Python Programming", "demand": 90, "supply": 75, "gap": 15},
    {"skill": "Docker / DevOps", "demand": 70, "supply": 40, "gap": 30}
]

CANDIDATES = [
    {
        "id": "cand_001",
        "name": "Alex De Silva",
        "email": "seeker@emploeralk.com",
        "title": "Junior Python Developer",
        "skills": ["Python", "SQL", "Git", "HTML", "CSS"],
        "resume_filename": "Alex_De_Silva_CV.pdf",
        "match_score": 0.0
    },
    {
        "id": "cand_002",
        "name": "Dilhani Perera",
        "email": "dilhani@gmail.com",
        "title": "Data Analyst",
        "skills": ["Python", "SQL", "Pandas", "Power BI", "Data Analytics"],
        "resume_filename": "Dilhani_Perera_Resume.pdf",
        "match_score": 0.0
    },
    {
        "id": "cand_003",
        "name": "Minura Gunasinghe",
        "email": "minura@yahoo.com",
        "title": "ML Enthusiast",
        "skills": ["Python", "Machine Learning", "SQL", "API Development", "Git"],
        "resume_filename": "Minura_ML_CV.pdf",
        "match_score": 0.0
    },
    {
        "id": "cand_004",
        "name": "Ruwan Fernando",
        "email": "ruwan@outlook.com",
        "title": "AWS Developer",
        "skills": ["AWS", "Cloud Computing", "Docker", "Git", "Python", "Bash"],
        "resume_filename": "Ruwan_Cloud_Architect.pdf",
        "match_score": 0.0
    }
]

SCRAPERS = {
    "linkedin": {"name": "LinkedIn Job Scraper", "status": "Idle", "last_run": "2026-08-23 10:15", "records_found": 142},
    "topjobs": {"name": "TopJobs.lk Scraper", "status": "Idle", "last_run": "2026-08-23 09:30", "records_found": 95},
    "indeed": {"name": "Indeed Scraper", "status": "Idle", "last_run": "2026-08-23 11:00", "records_found": 120},
    "coursera": {"name": "Coursera API Sync", "status": "Idle", "last_run": "2026-08-22 18:00", "records_found": 50},
    "survey": {"name": "Survey & CV Collector", "status": "Idle", "last_run": "2026-08-23 12:45", "records_found": 34}
}

