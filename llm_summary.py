import hashlib
import json
import os
import re
from pathlib import Path

try:
    import httpx
except ImportError:
    httpx = None

CACHE_PATH = Path(__file__).with_name("summary_cache.json")
API_KEY = os.environ.get("GROQ_API_KEY")
MODEL_NAME = os.environ.get("GROQ_MODEL", "groq-llama2-mini")
BASE_URL = os.environ.get("GROQ_API_URL", f"https://api.groq.com/v1/models/{MODEL_NAME}/outputs")


def _load_cache() -> dict:
    if not CACHE_PATH.exists():
        return {}
    try:
        return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_cache(cache: dict) -> None:
    try:
        CACHE_PATH.write_text(json.dumps(cache, indent=2), encoding="utf-8")
    except Exception:
        pass


def _cache_key(article: dict) -> str:
    digest = hashlib.sha256((article["title"] + article["link"]).encode()).hexdigest()
    return digest


def _build_extraction_prompt(article: dict) -> str:
    source_summary = article.get('summary', '').strip()
    if len(source_summary) > 800:
        source_summary = source_summary[:800] + "..."
    return (
        "You are a professional tech news editor. Extract structured data for a software engineer newsletter.\n\n"
        "RESPOND IN VALID JSON ONLY (no markdown, no extra text):\n"
        "{\n"
        '  "summary": "2-3 sentences, max 380 chars. What happened and why SWEs should care.",\n'
        '  "key_takeaways": ["takeaway 1", "takeaway 2"],\n'
        '  "impact_level": "HIGH or MEDIUM or LOW",\n'
        '  "category_tag": "FEATURE|RESEARCH|INCIDENT|TOOL|SECURITY|PERFORMANCE"\n'
        "}\n\n"
        f"Title: {article['title']}\n"
        f"Summary: {source_summary}\n\n"
        "Be factual. Extract, do not invent."
    )


def _call_groq(prompt: str) -> str:
    if not API_KEY or not httpx:
        return ""

    try:
        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "input": prompt,
            "max_output_tokens": 350,
            "temperature": 0.1,
        }
        with httpx.Client(timeout=45.0) as client:
            response = client.post(BASE_URL, headers=headers, json=payload)
            if response.status_code != 200:
                return ""
            data = response.json()

        if isinstance(data, dict):
            if "outputs" in data and data["outputs"]:
                output = data["outputs"][0]
                content = output.get("content")
                if isinstance(content, list):
                    return "".join(content).strip()
                elif isinstance(content, str):
                    return content.strip()
            if "output" in data and data["output"]:
                return str(data["output"]).strip()
            if "text" in data and data["text"]:
                return str(data["text"]).strip()
    except Exception:
        pass
    return ""


def _extract_json(text: str) -> dict:
    match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except Exception:
            pass
    return {}


def _fallback_structure(article: dict) -> dict:
    summary = article.get("summary", "").replace("\n", " ").strip()
    if len(summary) > 380:
        summary = summary[:380].rstrip() + "…"
    
    text_lower = (article.get("title", "") + " " + summary).lower()
    impact = "MEDIUM"
    if any(x in text_lower for x in ["security", "breach", "vulnerability", "critical", "outage"]):
        impact = "HIGH"
    elif any(x in text_lower for x in ["research", "arxiv", "paper", "study"]):
        impact = "LOW"
    
    tag = "TOOL"
    if "security" in text_lower:
        tag = "SECURITY"
    elif "arxiv" in text_lower or "research" in text_lower:
        tag = "RESEARCH"
    elif "release" in text_lower or "launch" in text_lower:
        tag = "FEATURE"
    elif "outage" in text_lower or "incident" in text_lower:
        tag = "INCIDENT"
    elif "performance" in text_lower or "faster" in text_lower:
        tag = "PERFORMANCE"
    
    return {
        "summary": summary,
        "key_takeaways": ["Read full article"],
        "impact_level": impact,
        "category_tag": tag
    }


def extract_article_structure(article: dict) -> dict:
    """Extract structured format: summary, takeaways, impact level."""
    key = _cache_key(article)
    cache = _load_cache()
    if key in cache:
        return cache[key]

    result = None
    if API_KEY:
        prompt = _build_extraction_prompt(article)
        response = _call_groq(prompt)
        if response:
            result = _extract_json(response)
            if result and "summary" in result and "key_takeaways" in result:
                cache[key] = result
                _save_cache(cache)
                return result

    result = _fallback_structure(article)
    cache[key] = result
    _save_cache(cache)
    return result


def explain_article(article: dict) -> str:
    """Backward compat: return summary string."""
    structure = extract_article_structure(article)
    return structure.get("summary", "")

