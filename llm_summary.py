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
    return (
        "You are a concise technical analyst. Summarize the following news item in 2-3 sentences, "
        "with a focus on what software engineers and technical leaders need to know. "
        "Include the core news, why it matters, and the impact it may have on products, architecture, or developer workflows.\n\n"
        f"Title: {article['title']}\n"
        f"Source: {article['source']}\n"
        f"Category: {article['category']}\n"
        f"Summary: {article.get('summary', '').strip()}"
    )


def _call_groq(prompt: str) -> str:
    if not API_KEY or not httpx:
        return ""

    try:
        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {"input": prompt, "max_output_tokens": 220}
        with httpx.Client(timeout=30.0) as client:
            response = client.post(BASE_URL, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

        if isinstance(data, dict):
            if "outputs" in data and data["outputs"]:
                output = data["outputs"][0]
                content = output.get("content")
                if isinstance(content, list):
                    return "".join(content).strip()
                if isinstance(content, str):
                    return content.strip()
            if "output" in data:
                return str(data["output"]).strip()
            if "text" in data:
                return str(data["text"]).strip()
    except Exception:
        return ""
    return ""


def explain_article(article: dict) -> str:
    key = _cache_key(article)
    cache = _load_cache()
    if key in cache:
        return cache[key]

    prompt = _build_prompt(article)
    summary = _call_groq(prompt).strip()
    if not summary:
        summary = article.get("summary", "").replace("\n", " ").strip()
        if summary:
            if len(summary) > 240:
                summary = summary[:240].rstrip() + "…"
            summary = f"Summary extracted from source: {summary}"
        else:
            summary = "No summary available."

    cache[key] = summary
    _save_cache(cache)
    return summary
