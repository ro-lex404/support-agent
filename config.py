import os
from dotenv import load_dotenv

# Load .env if present
load_dotenv()

class Config:
    LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "http://localhost:8080/v1")
    LLM_API_KEY: str = os.getenv("LLM_API_KEY", "not-needed")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "Qwen3.5-4B-Q4_K_M.gguf")
    MAX_ITERATIONS: int = int(os.getenv("MAX_ITERATIONS", "5"))
