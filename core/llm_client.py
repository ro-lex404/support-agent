from openai import OpenAI
from config import Config

def get_llm_client() -> OpenAI:
    """
    Returns an OpenAI-compatible client instance configured
    to point to our local llama.cpp server, Ollama, or remote provider.
    """
    return OpenAI(
        base_url=Config.LLM_BASE_URL,
        api_key=Config.LLM_API_KEY,
    )
