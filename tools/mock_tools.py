from datetime import datetime, timedelta
from typing import List, Dict, Any
from tools.base import tool

@tool(
    name="get_current_time",
    description="Returns the current local date, time, and day of the week."
)
def get_current_time() -> Dict[str, str]:
    now = datetime.now()
    return {
        "datetime": now.strftime("%Y-%m-%d %H:%M:%S"),
        "date": now.strftime("%Y-%m-%d"),
        "day": now.strftime("%A"),
        "time": now.strftime("%H:%M")
    }

@tool(
    name="list_unread_emails",
    description="Fetches recent unread emails from your inbox with subject, sender, and snippet."
)
def list_unread_emails(max_results: int = 5) -> List[Dict[str, Any]]:
    # Mock data simulating real emails
    today = datetime.now().strftime("%Y-%m-%d")
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    
    return [
        {
            "id": "msg_001",
            "sender": "recruiter@techcorp.io",
            "subject": "Interview Invitation: Junior AI Engineer",
            "date": today,
            "snippet": f"Hi! We loved your profile. Are you free for a 45-min technical chat tomorrow ({tomorrow}) at 3:00 PM?"
        },
        {
            "id": "msg_002",
            "sender": "newsletter@dailytech.com",
            "subject": "Top open-source models this week",
            "date": today,
            "snippet": "Discover the latest quantization techniques for llama.cpp and Qwen 2.5."
        }
    ][:max_results]

@tool(
    name="check_calendar_events",
    description="Retrieves scheduled events on your calendar for a specific date in YYYY-MM-DD format."
)
def check_calendar_events(date_str: str) -> List[Dict[str, str]]:
    # Mock schedule: Simulate a conflicting event on tomorrow's afternoon
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    
    if date_str == tomorrow:
        return [
            {
                "title": "CS401 Final Project Review",
                "start": f"{tomorrow} 14:30:00",
                "end": f"{tomorrow} 15:30:00",
                "location": "Room 302 / Zoom"
            }
        ]
    return []

@tool(
    name="search_job_postings",
    description="Searches for job postings matching a specific role keyword and returns title, company, requirements, and url."
)
def search_job_postings(role: str) -> List[Dict[str, Any]]:
    # Mock jobs
    return [
        {
            "id": "job_101",
            "title": "Junior AI / Agent Engineer",
            "company": "DeepAutomation Labs",
            "location": "Remote",
            "required_skills": ["Python", "LLMs", "llama.cpp", "FastAPI"],
            "url": "https://example.com/jobs/101"
        },
        {
            "id": "job_102",
            "title": "Backend Python Developer (Entry Level)",
            "company": "DataStream Inc",
            "location": "Hybrid",
            "required_skills": ["Python", "SQL", "Docker", "REST APIs"],
            "url": "https://example.com/jobs/102"
        }
    ]
