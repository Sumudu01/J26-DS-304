import time
from datetime import datetime
from flask import Flask, jsonify, request
from flask_cors import CORS

from mock_data import DEFAULT_USERS, JOBS, COURSES, SKILL_TRENDS, SKILL_DEMAND_VS_SUPPLY, CANDIDATES, SCRAPERS

app = Flask(__name__)
# Enable CORS for all routes to allow frontend connection
CORS(app)

# Helper function to get default required skills for popular roles if no matching job is found
def get_skills_for_role(role_name):
    role_lower = role_name.lower()
    if "ai" in role_lower or "artificial intelligence" in role_lower:
        return ["Python", "Machine Learning", "NLP", "Generative AI", "Git", "API Development"]
    elif "machine learning" in role_lower or "ml" in role_lower:
        return ["Python", "Machine Learning", "PyTorch", "AWS", "SQL", "Docker"]
    elif "cloud" in role_lower or "aws" in role_lower or "devops" in role_lower:
        return ["AWS", "Cloud Computing", "Docker", "Git", "Python", "Bash"]
    elif "data" in role_lower or "analytics" in role_lower:
        return ["Python", "SQL", "Pandas", "Power BI", "Data Analytics"]
    elif "software" in role_lower or "developer" in role_lower or "web" in role_lower:
        return ["Python", "JavaScript", "SQL", "Git", "HTML", "CSS"]
    else:
        # Default skills
        return ["Python", "Git", "SQL", "Communication"]

@app.route("/api/auth/login", methods=["POST"])
def login():
    data = request.json or {}
    email = data.get("email")
    password = data.get("password")
    
    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400
        
    user = DEFAULT_USERS.get(email)
    if user and user["password"] == password:
        # Return user details (excluding password)
        user_info = {k: v for k, v in user.items() if k != "password"}
        return jsonify({"status": "success", "user": user_info}), 200
    
    return jsonify({"error": "Invalid email or password"}), 401

@app.route("/api/auth/signup", methods=["POST"])
def signup():
    data = request.json or {}
    email = data.get("email")
    password = data.get("password")
    role = data.get("role")
    name = data.get("name")
    
    if not email or not password or not role or not name:
        return jsonify({"error": "All fields are required"}), 400
        
    if email in DEFAULT_USERS:
        return jsonify({"error": "User already exists with this email"}), 400
        
    new_user = {
        "email": email,
        "password": password,
        "role": role,
        "name": name
    }
    
    if role == "seeker":
        new_user["current_role"] = data.get("current_role", "Job Seeker")
        # Default starting skills
        new_user["skills"] = [s.strip() for s in data.get("skills", "").split(",") if s.strip()] or ["Python"]
        new_user["target_role"] = data.get("target_role", "AI Engineer")
        
        # Add to candidate database for recruiters to see
        CANDIDATES.append({
            "id": f"cand_{len(CANDIDATES) + 1:03d}",
            "name": name,
            "email": email,
            "title": new_user["current_role"],
            "skills": new_user["skills"],
            "resume_filename": "Uploaded_Resume.pdf",
            "match_score": 0.0
        })
    elif role == "recruiter":
        new_user["company"] = data.get("company", "Independent Recruiter")
        
    DEFAULT_USERS[email] = new_user
    
    user_info = {k: v for k, v in new_user.items() if k != "password"}
    return jsonify({"status": "success", "user": user_info}), 201

# User profile updates (specifically skills or target roles)
@app.route("/api/profile/update", methods=["POST"])
def update_profile():
    data = request.json or {}
    email = data.get("email")
    
    if not email or email not in DEFAULT_USERS:
        return jsonify({"error": "User not found"}), 404
        
    user = DEFAULT_USERS[email]
    if "skills" in data:
        user["skills"] = data["skills"]
        # Update candidates list as well
        for cand in CANDIDATES:
            if cand["email"] == email:
                cand["skills"] = data["skills"]
    if "target_role" in data:
        user["target_role"] = data["target_role"]
    if "current_role" in data:
        user["current_role"] = data["current_role"]
        for cand in CANDIDATES:
            if cand["email"] == email:
                cand["title"] = data["current_role"]
                
    user_info = {k: v for k, v in user.items() if k != "password"}
    return jsonify({"status": "success", "user": user_info}), 200

# Module 1: Demand Forecasting
@app.route("/api/demand-forecast", methods=["GET"])
def demand_forecast():
    return jsonify(SKILL_TRENDS), 200

# Module 2: Skill Gap Analysis
@app.route("/api/skill-gap", methods=["POST"])
def skill_gap():
    data = request.json or {}
    user_skills = data.get("skills", [])
    target_role = data.get("target_role", "AI Engineer")
    
    # Standardize casing for comparison
    user_skills_set = {s.lower() for s in user_skills}
    
    # Get required skills for target role
    required_skills = get_skills_for_role(target_role)
    
    matching_skills = []
    missing_skills = []
    
    for skill in required_skills:
        if skill.lower() in user_skills_set:
            matching_skills.append(skill)
        else:
            missing_skills.append(skill)
            
    # Find matching courses from Coursera based on missing skills
    recommended_courses = []
    missing_skills_lower = {s.lower() for s in missing_skills}
    
    for course in COURSES:
        # If the course teaches any of the missing skills
        teaches_missing = False
        for skill in course["skills_taught"]:
            if skill.lower() in missing_skills_lower:
                teaches_missing = True
                break
        if teaches_missing:
            recommended_courses.append(course)
            
    # Calculate match percentage
    match_percentage = int((len(matching_skills) / len(required_skills)) * 100) if required_skills else 100
            
    return jsonify({
        "target_role": target_role,
        "required_skills": required_skills,
        "matching_skills": matching_skills,
        "missing_skills": missing_skills,
        "match_percentage": match_percentage,
        "recommended_courses": recommended_courses
    }), 200

# Module 3: Career Path Planner
@app.route("/api/career-path", methods=["POST"])
def career_path():
    data = request.json or {}
    current_role = data.get("current_role", "Junior Developer")
    target_role = data.get("target_role", "AI Engineer")
    
    # Simple rule-based career roadmap generator
    steps = []
    
    if "junior" in current_role.lower() and "ai" in target_role.lower():
        steps = [
            {
                "step": 1,
                "title": "Consolidate Python & Backend Fundamentals",
                "description": "Strengthen API design, async execution, git workflows, and relational database queries.",
                "duration": "1-2 months",
                "skills_to_acquire": ["Git", "API Development", "SQL"],
                "status": "completed"
            },
            {
                "step": 2,
                "title": "Master Core Machine Learning Concepts",
                "description": "Learn mathematical foundations, regression, classification algorithms, and evaluation metrics using Scikit-Learn.",
                "duration": "2-3 months",
                "skills_to_acquire": ["Machine Learning", "Python"],
                "status": "in-progress"
            },
            {
                "step": 3,
                "title": "Deep Dive into Neural Networks & NLP",
                "description": "Study artificial neural networks, transformers, sequence processing, and language models with PyTorch.",
                "duration": "2-3 months",
                "skills_to_acquire": ["Deep Learning", "NLP"],
                "status": "locked"
            },
            {
                "step": 4,
                "title": "Generative AI Systems & Deployment",
                "description": "Develop multi-agent solutions using LLM APIs, vector databases, prompt engineering patterns, and Docker deployment.",
                "duration": "1-2 months",
                "skills_to_acquire": ["Generative AI", "Prompt Engineering"],
                "status": "locked"
            }
        ]
    elif "data" in current_role.lower() and "ai" in target_role.lower():
        steps = [
            {
                "step": 1,
                "title": "Data Engineering & Pipeline Scalability",
                "description": "Optimize python data manipulation, pandas processing, and move structured data streams efficiently.",
                "duration": "1 month",
                "skills_to_acquire": ["Python", "SQL", "Pandas"],
                "status": "completed"
            },
            {
                "step": 2,
                "title": "Predictive Modeling and Statistical AI",
                "description": "Construct classifiers and regressors, and master validation strategies using Scikit-Learn.",
                "duration": "2 months",
                "skills_to_acquire": ["Machine Learning"],
                "status": "in-progress"
            },
            {
                "step": 3,
                "title": "LLMs, Prompt Engineering, and RAG",
                "description": "Integrate Large Language Models, build vector databases, and perform Retrieval-Augmented Generation.",
                "duration": "2 months",
                "skills_to_acquire": ["Generative AI", "Prompt Engineering", "NLP"],
                "status": "locked"
            }
        ]
    else:
        # Default step progression
        steps = [
            {
                "step": 1,
                "title": "Strengthen Core Prerequisites",
                "description": f"Learn underlying technologies required for transitioning from {current_role}.",
                "duration": "2 months",
                "skills_to_acquire": ["Python", "Git"],
                "status": "in-progress"
            },
            {
                "step": 2,
                "title": "Transition to Intermediate Frameworks",
                "description": "Gain competencies matching the technical stack used in industry.",
                "duration": "3 months",
                "skills_to_acquire": ["SQL", "API Development"],
                "status": "locked"
            },
            {
                "step": 3,
                "title": "Target Role Specialization",
                "description": f"Focus fully on tools and workflows aligned with a {target_role} position.",
                "duration": "3 months",
                "skills_to_acquire": get_skills_for_role(target_role)[:3],
                "status": "locked"
            }
        ]
        
    return jsonify({
        "current_role": current_role,
        "target_role": target_role,
        "roadmap": steps,
        "estimated_duration": "6 - 10 months total"
    }), 200

# Module 4: Skill Matching & Job Alignment
@app.route("/api/matching-jobs", methods=["POST"])
def matching_jobs():
    data = request.json or {}
    user_skills = data.get("skills", [])
    
    # Make sure we have lowercase skills for case-insensitive matching
    user_skills_set = {s.lower() for s in user_skills}
    
    matched_jobs = []
    
    for job in JOBS:
        req_skills = job["required_skills"]
        if not req_skills:
            score = 100
            matching = []
            missing = []
        else:
            matching = [s for s in req_skills if s.lower() in user_skills_set]
            missing = [s for s in req_skills if s.lower() not in user_skills_set]
            score = int((len(matching) / len(req_skills)) * 100)
            
        job_copy = job.copy()
        job_copy["match_score"] = score
        job_copy["matching_skills"] = matching
        job_copy["missing_skills"] = missing
        
        matched_jobs.append(job_copy)
        
    # Sort by compatibility score descending
    matched_jobs.sort(key=lambda x: x["match_score"], reverse=True)
    
    return jsonify(matched_jobs), 200

# Recruiter: Add and view posted jobs
@app.route("/api/recruiter/posted-jobs", methods=["GET", "POST"])
def posted_jobs():
    if request.method == "POST":
        data = request.json or {}
        title = data.get("title")
        company = data.get("company", "Recruiter Company")
        platform = data.get("platform", "Recruiter Panel")
        location = data.get("location", "Colombo, Sri Lanka")
        description = data.get("description", "")
        required_skills = data.get("required_skills", [])
        salary = data.get("salary", "Negotiable")
        
        if not title or not required_skills:
            return jsonify({"error": "Job title and required skills are required"}), 400
            
        new_job = {
            "id": f"job_{len(JOBS) + 1:03d}",
            "title": title,
            "company": company,
            "platform": platform,
            "location": location,
            "description": description,
            "required_skills": required_skills,
            "salary": salary,
            "posted_date": datetime.today().strftime("%Y-%m-%d")
        }
        JOBS.append(new_job)
        return jsonify({"status": "success", "job": new_job}), 201
        
    # GET: return jobs posted via the recruiter panel
    recruiter_jobs = [j for j in JOBS if j["platform"] in ["Recruiter Panel", "LinkedIn", "Indeed", "TopJobs.lk"]]
    return jsonify(recruiter_jobs), 200

# Recruiter: Find matching candidates for a job
@app.route("/api/recruiter/matching-candidates", methods=["GET"])
def matching_candidates():
    job_id = request.args.get("job_id")
    if not job_id:
        return jsonify({"error": "job_id parameter is required"}), 400
        
    # Find the job
    job = next((j for j in JOBS if j["id"] == job_id), None)
    if not job:
        return jsonify({"error": "Job not found"}), 404
        
    req_skills = {s.lower() for s in job["required_skills"]}
    matched_candidates = []
    
    for cand in CANDIDATES:
        cand_skills = cand["skills"]
        matching = [s for s in cand_skills if s.lower() in req_skills]
        missing = [s for s in job["required_skills"] if s.lower() not in {cs.lower() for cs in cand_skills}]
        
        score = int((len(matching) / len(job["required_skills"])) * 100) if job["required_skills"] else 100
        
        cand_copy = cand.copy()
        cand_copy["match_score"] = score
        cand_copy["matching_skills"] = matching
        cand_copy["missing_skills"] = missing
        
        matched_candidates.append(cand_copy)
        
    matched_candidates.sort(key=lambda x: x["match_score"], reverse=True)
    return jsonify(matched_candidates), 200

# Recruiter: Skill supply/demand analytics
@app.route("/api/recruiter/market-analytics", methods=["GET"])
def market_analytics():
    return jsonify(SKILL_DEMAND_VS_SUPPLY), 200

# Admin: Metrics
@app.route("/api/admin/metrics", methods=["GET"])
def admin_metrics():
    # Count from our databases
    metrics = {
        "total_jobs": len(JOBS),
        "total_courses": len(COURSES),
        "total_candidates": len(CANDIDATES),
        "total_users": len(DEFAULT_USERS),
        "scrapers_active": sum(1 for s in SCRAPERS.values() if s["status"] == "Scraping..."),
        "system_status": "Healthy",
        "last_sync": datetime.today().strftime("%Y-%m-%d %H:%M:%S")
    }
    return jsonify(metrics), 200

# Admin: View all scrapers
@app.route("/api/admin/scrapers", methods=["GET"])
def get_scrapers():
    return jsonify(SCRAPERS), 200

# Admin: Trigger scraper simulation
@app.route("/api/admin/scrape", methods=["POST"])
def trigger_scrape():
    data = request.json or {}
    scraper_id = data.get("scraper_id")
    
    if not scraper_id or scraper_id not in SCRAPERS:
        return jsonify({"error": "Invalid scraper ID"}), 400
        
    scraper = SCRAPERS[scraper_id]
    
    # Simulate a brief scraping activity
    scraper["status"] = "Scraping..."
    scraper["last_run"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    # Return immediately to simulate non-blocking, we update count dynamically
    import random
    new_records = random.randint(10, 50)
    scraper["records_found"] += new_records
    scraper["status"] = "Idle"
    
    # If jobs were scraped, add a dummy job to simulate data gathering
    if scraper_id in ["linkedin", "indeed", "topjobs"]:
        platform_names = {"linkedin": "LinkedIn", "indeed": "Indeed", "topjobs": "TopJobs.lk"}
        platform = platform_names[scraper_id]
        
        # Add a newly discovered job
        new_job_id = f"job_scraped_{len(JOBS) + 1:03d}"
        new_job = {
            "id": new_job_id,
            "title": f"Newly Scraped AI Role ({new_records}th batch)",
            "company": "Innovative AI Corp",
            "platform": platform,
            "location": "Colombo, Sri Lanka",
            "description": f"Automated scrape matched job details. Required core AI skills.",
            "required_skills": ["Python", "Machine Learning", "Generative AI"],
            "salary": "LKR 250,000+",
            "posted_date": datetime.today().strftime("%Y-%m-%d")
        }
        JOBS.append(new_job)
        
    return jsonify({"status": "success", "scraper": scraper}), 200

# Mock CV upload endpoint
@app.route("/api/seeker/upload-cv", methods=["POST"])
def upload_cv():
    if "cv" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
        
    file = request.files["cv"]
    email = request.form.get("email")
    
    if not email or email not in DEFAULT_USERS:
        return jsonify({"error": "User email not found"}), 404
        
    # Simulate CV skill parsing
    # Let's say we parsed "Generative AI", "Machine Learning", and "NLP" from their CV
    parsed_skills = ["Python", "SQL", "Git", "Machine Learning", "Generative AI", "NLP"]
    
    user = DEFAULT_USERS[email]
    user["skills"] = parsed_skills
    
    # Also update candidates database
    for cand in CANDIDATES:
        if cand["email"] == email:
            cand["skills"] = parsed_skills
            cand["resume_filename"] = file.filename
            
    return jsonify({
        "status": "success",
        "filename": file.filename,
        "parsed_skills": parsed_skills,
        "user": {k: v for k, v in user.items() if k != "password"}
    }), 200

if __name__ == "__main__":
    app.run(port=5000, debug=True)

