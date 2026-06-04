"""
daily_digest.py — Personalized daily tech briefing for a software engineer.
Aggregates high-signal feeds, ranks important stories, and adds a concise
LLM-generated explanation for each selected item.
"""

import datetime
import hashlib
import os
import re
from collections import defaultdict

import feedparser
from dateutil import parser as dateparser

from llm_summary import explain_article, extract_article_structure

# ─────────────────────────────────────────────
#  SOURCE CONFIGURATION
#  Add/remove feeds freely. Each entry is:
#  (feed_url, display_name, quality_score 1-5)
# ─────────────────────────────────────────────

SOURCES = {
    "⚙️ Software Engineering": [
        ("https://news.ycombinator.com/rss", "Hacker News", 5),
        ("https://rss.reddit.com/r/programming/.rss", "r/programming", 4),
        ("https://infoq.com/feed/", "InfoQ", 5),
        ("https://dev.to/feed", "DEV Community", 4),
        ("https://stackoverflow.blog/feed/", "Stack Overflow Blog", 4),
        ("https://github.blog/feed/", "GitHub Blog", 4),
        ("https://aws.amazon.com/blogs/aws/feed/", "AWS News Blog", 4),
        ("https://devblogs.microsoft.com/azure/feed/", "Microsoft Azure Blog", 4),
        ("https://cloud.google.com/blog/rss.xml", "Google Cloud Blog", 4),
        ("https://netflixtechblog.com/feed", "Netflix Tech Blog", 4),
    ],
    "🤖 AI & Machine Learning": [
        ("https://arxiv.org/rss/cs.AI", "arXiv cs.AI", 5),
        ("https://arxiv.org/rss/cs.LG", "arXiv cs.LG", 5),
        ("https://arxiv.org/rss/cs.SE", "arXiv cs.SE", 5),
        ("https://rss.reddit.com/r/MachineLearning/.rss", "r/MachineLearning", 4),
        ("https://rss.reddit.com/r/LocalLLaMA/.rss", "r/LocalLLaMA", 4),
        ("https://rss.reddit.com/r/mlops/.rss", "r/MLOps", 4),
        ("https://huggingface.co/blog/feed", "HuggingFace Blog", 5),
        ("https://bair.berkeley.edu/blog/feed.xml", "BAIR Blog", 5),
        ("https://ai.googleblog.com/atom.xml", "Google AI Blog", 5),
        ("https://openai.com/blog/rss/", "OpenAI Blog", 5),
    ],
    "🌐 General Tech & Shifts": [
        ("https://arstechnica.com/feed/", "Ars Technica", 5),
        ("https://www.theverge.com/rss/index.xml", "The Verge", 4),
        ("https://techcrunch.com/feed/", "TechCrunch", 4),
        ("https://rss.reddit.com/r/technology/.rss", "r/technology", 3),
        ("https://feeds.wired.com/wired/index", "Wired", 4),
        ("https://www.technologyreview.com/feed/", "MIT Tech Review", 5),
        ("https://www.bloomberg.com/technology/rss", "Bloomberg Technology", 4),
        ("https://www.fastcompany.com/section/tech/feed", "Fast Company Tech", 3),
        ("https://www.theregister.com/headlines.rss", "The Register", 4),
        ("https://www.darkreading.com/rss.xml", "Dark Reading", 4),
    ],
}

# ─────────────────────────────────────────────
#  KEYWORD BOOSTS
# ─────────────────────────────────────────────

HIGH_VALUE_KEYWORDS = [
    "LLM", "GPT", "AI", "machine learning", "deep learning", "agent",
    "benchmark", "performance", "architecture", "scaling", "cloud",
    "kubernetes", "microservices", "observability", "rust", "golang",
    "open source", "release", "security", "privacy", "regulation",
    "incident", "outage", "migration", "upgrade", "compliance",
    "productivity", "developer experience", "automation",
]

# ─────────────────────────────────────────────
#  CONFIGURATION
# ─────────────────────────────────────────────

MAX_AGE_HOURS = int(os.environ.get("MAX_AGE_HOURS", 42))
HIGHLIGHT_COUNT = int(os.environ.get("HIGHLIGHT_COUNT", 3))
CATEGORY_COUNT = int(os.environ.get("CATEGORY_COUNT", 3))
MIN_ACCEPTED_SCORE = float(os.environ.get("MIN_ACCEPTED_SCORE", 8.8))

CATEGORY_ORDER = [
    "⚙️ Software Engineering",
    "🤖 AI & Machine Learning",
    "🌐 General Tech & Shifts",
]

# ─────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────

def clean_html(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def parse_date(entry) -> datetime.datetime:
    for field in ("published", "updated", "created"):
        val = entry.get(field)
        if val:
            try:
                return dateparser.parse(val)
            except Exception:
                pass

    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if parsed:
        try:
            return datetime.datetime.fromtimestamp(
                datetime.datetime(*parsed[:6]).timestamp(),
                tz=datetime.timezone.utc,
            )
        except Exception:
            pass

    return datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=2)


def hours_ago(dt: datetime.datetime) -> float:
    now = datetime.datetime.now(datetime.timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    return (now - dt).total_seconds() / 3600.0


def keyword_score(title: str, summary: str) -> float:
    text = (title + " " + summary).lower()
    return sum(1 for keyword in HIGH_VALUE_KEYWORDS if keyword.lower() in text)


def deduplicate(articles: list) -> list:
    seen = set()
    unique = []
    for article in articles:
        fingerprint = re.sub(r"\W+", "", (article["title"] + article["link"]).lower())
        key = hashlib.sha256(fingerprint.encode()).hexdigest()[:18]
        if key not in seen:
            seen.add(key)
            unique.append(article)
    return unique


# ─────────────────────────────────────────────
#  CORE PIPELINE
# ─────────────────────────────────────────────


def score_article(title: str, summary: str, quality: int, age_hours: float) -> float:
    source_score = float(quality) * 1.8
    recency_score = 6.0 * (2.718281828459045 ** (-age_hours / 18.0))
    kw_score = keyword_score(title, summary) * 1.4
    richness_bonus = min(1.5, len(summary) / 210.0)
    return round(source_score + recency_score + kw_score + richness_bonus, 2)


def fetch_all_feeds(max_age_hours: int = MAX_AGE_HOURS) -> list:
    articles = []
    stats = {"fetched": 0, "skipped": 0, "errors": 0}

    for category, feeds in SOURCES.items():
        for url, source_name, quality in feeds:
            try:
                feed = feedparser.parse(url, request_headers={
                    "User-Agent": "DailyUpdateMailer/1.0 (+https://github.com)"
                })
                for entry in feed.entries[:18]:
                    published = parse_date(entry)
                    age = hours_ago(published)
                    if age > max_age_hours:
                        stats["skipped"] += 1
                        continue

                    title = clean_html(entry.get("title", "No title"))
                    raw_summary = entry.get("summary", entry.get("description", "")) or ""
                    summary = clean_html(raw_summary)
                    link = entry.get("link", "#")

                    score = score_article(title, summary, quality, age)
                    articles.append({
                        "title": title,
                        "link": link,
                        "summary": summary,
                        "category": category,
                        "source": source_name,
                        "published": published,
                        "score": score,
                        "age_hours": round(age, 1),
                    })
                    stats["fetched"] += 1
            except Exception as e:
                stats["errors"] += 1
                print(f"  [WARN] Failed to fetch {source_name}: {e}")

    print(f"\n📊 Feed stats: {stats['fetched']} fetched, {stats['skipped']} skipped, {stats['errors']} errors")
    return articles


def select_top_articles(articles: list, per_category: int = CATEGORY_COUNT, global_top: int = HIGHLIGHT_COUNT) -> dict:
    deduped = deduplicate(articles)
    deduped.sort(key=lambda item: item["score"], reverse=True)

    accepted = [item for item in deduped if item["score"] >= MIN_ACCEPTED_SCORE]
    if not accepted:
        accepted = deduped[: max(global_top, per_category * len(CATEGORY_ORDER))]

    highlights = accepted[:global_top]
    by_category = defaultdict(list)
    for article in accepted:
        if len(by_category[article["category"]]) < per_category:
            by_category[article["category"]].append(article)

    return {
        "highlights": highlights,
        "by_category": {category: by_category.get(category, []) for category in CATEGORY_ORDER},
        "total_collected": len(accepted),
    }


def attach_explanations(data: dict) -> None:
    for article in data.get("highlights", []) + [item for group in data.get("by_category", {}).values() for item in group]:
        structure = extract_article_structure(article)
        article["structure"] = structure
        article["llm_summary"] = structure.get("summary", "")


def format_article(article: dict, index: int = None) -> str:
    prefix = f"**{index}.** " if index is not None else "- "
    published_ts = article["published"].strftime("%Y-%m-%d %H:%M UTC")

    lines = [
        f"{prefix}[**{article['title']}**]({article['link']})",
        f"*{article['source']} · {published_ts}*",
    ]

    structure = article.get("structure", {})
    if structure:
        impact = structure.get("impact_level", "MEDIUM")
        tag = structure.get("category_tag", "TOOL")
        lines.append(f"🔴 {impact} · 🏷️ {tag}")
        
        summary = structure.get("summary", "")
        if summary:
            lines.append(f"  {summary}")
        
        takeaways = structure.get("key_takeaways", [])
        if takeaways:
            for takeaway in takeaways[:2]:
                lines.append(f"  • {takeaway}")
    else:
        summary_text = article.get("llm_summary") or article.get("summary", "").replace("\n", " ").strip()
        if summary_text:
            if len(summary_text) > 400:
                summary_text = summary_text[:400].rstrip() + "…"
            lines.append(f"  {summary_text}")

    lines.append("")
    return "\n".join(lines)


def generate_digest(data: dict) -> str:
    today = datetime.date.today()
    date_str = today.strftime("%B %d, %Y")
    lines = [
        f"# Daily Update Mailer — {date_str}",
        "> Daily briefing optimized for a software engineer seeking competitive tech advantage.",
        "---",
        "",
        "## Executive Highlights",
        "The top stories selected for maximum professional impact.",
        "",
    ]

    for index, article in enumerate(data["highlights"], start=1):
        lines.append(format_article(article, index=index))

    lines.append("---")
    lines.append("")

    for category in CATEGORY_ORDER:
        articles = data["by_category"].get(category, [])
        if not articles:
            continue
        lines.append(f"## {category}")
        lines.append("")
        for index, article in enumerate(articles, start=1):
            lines.append(format_article(article, index=index))
        lines.append("---")
        lines.append("")

    lines.append(
        f"*Generated at {datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} · "
        f"Sources: {sum(len(v) for v in SOURCES.values())} feeds across {len(CATEGORY_ORDER)} categories.*"
    )
    return "\n".join(lines)


def main() -> None:
    print("🚀 Starting Daily Update Mailer...")
    print(f"📅 Date: {datetime.date.today()}")
    print(f"📡 Feeds configured: {sum(len(v) for v in SOURCES.values())}")

    articles = fetch_all_feeds()
    if not articles:
        print("⚠️ No articles fetched. Check your internet connection or feed configuration.")
        return

    data = select_top_articles(articles)
    attach_explanations(data)
    digest = generate_digest(data)

    output_path = os.environ.get("DIGEST_OUTPUT", "digest.md")
    with open(output_path, "w", encoding="utf-8") as writer:
        writer.write(digest)

    print(f"\n✅ Digest written to {output_path}")
    print(f"📰 Highlights: {len(data['highlights'])} items")
    print(f"📂 Categories included: {[category for category, items in data['by_category'].items() if items]}")


if __name__ == "__main__":
    main()
