import re
import urllib.request
from typing import List, Dict, Any
from bs4 import BeautifulSoup
from ddgs import DDGS
from tools.base import tool

@tool(
    name="search_web",
    description="Searches DuckDuckGo for live information, articles, news, or job postings. Returns top titles, URLs, and snippets."
)
def search_web(query: str, max_results: int = 4) -> List[Dict[str, str]]:
    """
    Searches the web via DuckDuckGo without tracking or cookies.
    """
    try:
        results = []
        with DDGS() as ddgs:
            raw_results = list(ddgs.text(query, max_results=max_results))
            for r in raw_results:
                results.append({
                    "title": r.get("title", ""),
                    "url": r.get("href", ""),
                    "snippet": r.get("body", "")
                })
        return results if results else [{"message": f"No results found for query: '{query}'"}]
    except Exception as e:
        return [{"error": f"Search failed: {str(e)}"}]

@tool(
    name="read_webpage",
    description="Fetches and extracts clean, readable text from a specific webpage URL (truncated to 1,200 characters to conserve context)."
)
def read_webpage(url: str) -> Dict[str, Any]:
    """
    Fetches a webpage, strips scripts and HTML boilerplate, and returns clean article text.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=5.0) as response:
            html = response.read().decode("utf-8", errors="ignore")
            
        soup = BeautifulSoup(html, "html.parser")
        
        # Strip non-content tags
        for element in soup(["script", "style", "nav", "footer", "header", "aside", "noscript", "svg"]):
            element.extract()
            
        # Get clean text
        text = soup.get_text(separator=" ", strip=True)
        # Collapse multiple spaces and newlines
        clean_text = re.sub(r"\s+", " ", text).strip()
        
        # Hard truncate to 1,200 characters to preserve 2048 token budget
        truncated_text = clean_text[:1200]
        
        return {
            "url": url,
            "text": truncated_text if truncated_text else "(No readable text found on page)",
            "length": len(truncated_text)
        }
    except Exception as e:
        return {"url": url, "error": f"Failed to fetch webpage: {str(e)}"}
