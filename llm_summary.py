import hashlib
import json
import os
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
    digest = hashlib.sha256((article["title"] + article["link"] + article.get("summary", "")).encode()).hexdigest()
    return digest


def _build_prompt(article: dict) -> str:
    source_summary = article.get('summary', '').strip()
    return (
        "You are a senior technical analyst and industry expert writing for enterprise software engineers and technical leaders.\n\n"
        "TASK: Provide a comprehensive, detailed analysis of the following tech news that enables readers to understand "
        "the significance, implications, and actionable insights WITHOUT reading the original article.\n\n"
        "REQUIREMENTS:\n"
        "1. START with the core news and its immediate impact (1-2 sentences)\n"
        "2. EXPLAIN technical implications, architecture shifts, or engineering practices affected (2-3 sentences)\n"
        "3. DETAIL business and operational impact for software organizations (1-2 sentences)\n"
        "4. LIST key takeaways or action items for engineering teams (2-3 bullet points)\n"
        "5. MENTION any risks, adoption barriers, or considerations (1 sentence if applicable)\n\n"
        "STYLE: Professional, technical, direct. Assume the reader has 5+ years of software engineering experience.\n"
        "AVOID: Generic statements, marketing language, or filler. Be specific and factual.\n\n"
        f"ARTICLE:\n"
        f"Title: {article['title']}\n"
        f"Source: {article['source']}\n"
        f"Category: {article['category']}\n"
        f"Summary: {source_summary}\n\n"
        "ANALYSIS:"
    )


def _call_groq(prompt: str) -> str:
    if not API_KEY:
        print("  [INFO] GROQ_API_KEY not set; skipping LLM enrichment.")
        return ""
    if not httpx:
        print("  [WARN] httpx not installed; cannot call Groq API.")
        return ""

    try:
        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        }
        # Use faster model with larger token limit for enterprise-grade summaries
        payload = {
            "input": prompt,
            "max_output_tokens": 650,  # Increased for detailed analysis
            "temperature": 0.3,  # Lower temp for factual, consistent output
        }
        with httpx.Client(timeout=45.0) as client:
            response = client.post(BASE_URL, headers=headers, json=payload)
            if response.status_code != 200:
                print(f"  [WARN] Groq API returned status {response.status_code}")
                return ""
            data = response.json()

        if isinstance(data, dict):
            if "outputs" in data and data["outputs"]:
                output = data["outputs"][0]
                content = output.get("content")
                if isinstance(content, list):
                    result = "".join(content).strip()
                elif isinstance(content, str):
                    result = content.strip()
                else:
                    return ""
                if result and len(result) > 100:
                    return result
            if "output" in data and data["output"]:
                return str(data["output"]).strip()
            if "text" in data and data["text"]:
                return str(data["text"]).strip()
    except httpx.TimeoutException:
        print("  [WARN] Groq API timeout; using fallback summary.")
    except httpx.HTTPError as e:
        print(f"  [WARN] Groq API error: {e}")
    except Exception as e:
        print(f"  [WARN] Unexpected error calling Groq: {e}")
    return ""


def explain_article(article: dict) -> str:
    key = _cache_key(article)
    cache = _load_cache()
    if key in cache:
        return cache[key]

    prompt = _build_prompt(article)
    summary = _call_groq(prompt).strip()
    
    if not summary:
        source_text = article.get("summary", "").replace("\n", " ").strip()
        if source_text:
            summary = source_text
        else:
            summary = "No detailed summary available."

    cache[key] = summary
    _save_cache(cache)
    return summary
