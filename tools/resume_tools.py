import os
import re
from typing import Dict, Any, List
from tools.base import tool

RESUME_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "resume.txt")

def _load_resume_text() -> str:
    if os.path.exists(RESUME_PATH):
        try:
            with open(RESUME_PATH, "r", encoding="utf-8") as f:
                return f.read()
        except Exception:
            return ""
    return ""

def _extract_known_skills() -> List[str]:
    """Extracts lowercase skill tokens from resume."""
    text = _load_resume_text().lower()
    common_skills = [
        "python", "c++", "sql", "bash", "javascript", "pytorch",
        "transformers", "llama.cpp", "lora", "qlora", "fine-tuning",
        "agentic", "scikit-learn", "fastapi", "flask", "docker",
        "rest api", "git", "linux", "postgresql", "sqlite",
        "vector database", "chromadb", "faiss", "machine learning",
        "deep learning", "llm", "nlp"
    ]
    return [skill for skill in common_skills if skill in text]

@tool(
    name="get_my_resume_summary",
    description="Reads the user's stored resume from disk and returns their education, skills, target roles, and strengths."
)
def get_my_resume_summary() -> Dict[str, Any]:
    text = _load_resume_text()
    if not text:
        return {"error": "No resume found in data/resume.txt. Please add your resume details there."}
    
    skills = _extract_known_skills()
    return {
        "status": "success",
        "skills_detected": skills,
        "education": "4th Year Undergraduate in Computer Science",
        "target_roles": ["Junior AI Engineer", "AI Developer Intern", "Junior Python Developer"],
        "resume_preview": text[:600]
    }

@tool(
    name="analyze_job_fit",
    description="Deterministically compares a job posting against your resume to calculate skill match percentage, overlapping skills, and missing requirements."
)
def analyze_job_fit(job_title: str, required_skills: str, job_snippet: str = "") -> Dict[str, Any]:
    resume_skills = set(_extract_known_skills())
    
    # Parse required skills from comma-separated string or text
    req_tokens = re.split(r"[,;/|\n]", required_skills.lower())
    clean_reqs = set()
    for token in req_tokens:
        cleaned = token.strip()
        if len(cleaned) > 1:
            clean_reqs.add(cleaned)
            
    if not clean_reqs:
        # Fallback check against words in snippet
        combined_text = (job_title + " " + job_snippet).lower()
        clean_reqs = {s for s in ["python", "pytorch", "c++", "sql", "docker", "fastapi", "git", "llm", "linux"] if s in combined_text}

    matching = []
    missing = []
    
    for req in clean_reqs:
        # Check if any resume skill matches or is a substring
        if any(req in r or r in req for r in resume_skills):
            matching.append(req)
        else:
            missing.append(req)
            
    total = len(matching) + len(missing)
    score = round((len(matching) / total * 100), 1) if total > 0 else 50.0

    return {
        "job_title": job_title,
        "match_percentage": score,
        "matching_skills": matching,
        "missing_skills": missing,
        "is_recommended": score >= 60.0,
        "assessment": "High Fit" if score >= 75 else ("Moderate Fit" if score >= 50 else "Low Fit")
    }
