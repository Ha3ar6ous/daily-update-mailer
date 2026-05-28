"""
daily_digest.py — Free Daily Tech Briefing Pipeline
Aggregates RSS feeds from top SE, AI, Cybersecurity, and Tech sources.
Ranks by recency + source quality, generates a clean Markdown digest.
"""

import feedparser
import datetime
import os
import re
import hashlib
from dateutil import parser as dateparser
from collections import defaultdict

# ─────────────────────────────────────────────
#  SOURCE CONFIGURATION
#  Add/remove feeds freely. Each entry is:
#  (feed_url, display_name, quality_score 1-5)
# ─────────────────────────────────────────────

SOURCES = {
    "⚙️ Software Engineering": [
        ("https://news.ycombinator.com/rss",              "Hacker News",        5),
        ("https://rss.reddit.com/r/programming/.rss",     "r/programming",      4),
        ("https://rss.reddit.com/r/devops/.rss",          "r/devops",           3),
        ("https://rss.reddit.com/r/sre/.rss",             "r/sre",              3),
        ("https://rss.reddit.com/r/golang/.rss",          "r/golang",           3),
        ("https://rss.reddit.com/r/rust/.rss",            "r/rust",             3),
        ("https://stackoverflow.blog/feed/",              "Stack Overflow Blog",4),
        ("https://engineering.fb.com/feed/",              "Meta Engineering",   4),
        ("https://netflixtechblog.com/feed",              "Netflix Tech Blog",  4),
        ("https://slack.engineering/feed",                "Slack Engineering",  4),
    ],
    "🤖 AI & Machine Learning": [
        ("https://arxiv.org/rss/cs.AI",                   "arXiv cs.AI",        5),
        ("https://arxiv.org/rss/cs.LG",                   "arXiv cs.LG",        5),
        ("https://arxiv.org/rss/cs.SE",                   "arXiv cs.SE",        5),
        ("https://rss.reddit.com/r/MachineLearning/.rss", "r/MachineLearning",  4),
        ("https://rss.reddit.com/r/LocalLLaMA/.rss",      "r/LocalLLaMA",       4),
        ("https://rss.reddit.com/r/mlops/.rss",           "r/MLOps",            3),
        ("https://huggingface.co/blog/feed",              "HuggingFace Blog",   5),
        ("https://bair.berkeley.edu/blog/feed.xml",       "BAIR Blog",          5),
        ("https://ai.googleblog.com/atom.xml",            "Google AI Blog",     5),
    ],
    "🔐 Cybersecurity": [
        ("https://krebsonsecurity.com/feed/",             "Krebs on Security",  5),
        ("https://www.schneier.com/blog/feed/",           "Schneier on Security",5),
        ("https://www.bleepingcomputer.com/feed/",        "BleepingComputer",   4),
        ("https://rss.reddit.com/r/cybersecurity/.rss",   "r/cybersecurity",    4),
        ("https://rss.reddit.com/r/netsec/.rss",          "r/netsec",           5),
        ("https://feeds.feedburner.com/TheHackersNews",   "The Hacker News",    4),
        ("https://www.darkreading.com/rss.xml",           "Dark Reading",       4),
        ("https://isc.sans.edu/rssfeed_full.xml",         "SANS ISC",           5),
    ],
    "🌐 General Tech & Shifts": [
        ("https://arstechnica.com/feed/",                 "Ars Technica",       5),
        ("https://www.theverge.com/rss/index.xml",        "The Verge",          4),
        ("https://techcrunch.com/feed/",                  "TechCrunch",         4),
        ("https://rss.reddit.com/r/technology/.rss",      "r/technology",       3),
        ("https://feeds.wired.com/wired/index",           "Wired",              4),
        ("https://www.technologyreview.com/feed/",        "MIT Tech Review",    5),
    ],
}

# ─────────────────────────────────────────────
#  KEYWORD BOOSTS — articles with these get +1 score
# ─────────────────────────────────────────────

HIGH_VALUE_KEYWORDS = [
    "vulnerability", "exploit", "breach", "zero-day", "CVE",
    "LLM", "GPT", "agent", "open source", "release", "benchmark",
    "performance", "architecture", "kubernetes", "rust", "golang",
    "distributed", "database", "compiler", "security", "AI",
    "announced", "launched", "critical", "emergency", "update",
    "outage", "incident", "postmortem", "redesign", "migration"
]

# ─────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────

def clean_html(text: str) -> str:
    """Strip HTML tags and normalize whitespace."""
    text = re.sub(r'<[^>]+>', ' ', text or '')
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def parse_date(entry) -> datetime.datetime:
    """Try multiple date fields to get publish time."""
    for field in ('published', 'updated', 'created'):
        val = entry.get(field)
        if val:
            try:
                return dateparser.parse(val)
            except Exception:
                pass
    return datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=2)

def hours_ago(dt: datetime.datetime) -> float:
    now = datetime.datetime.now(datetime.timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    return (now - dt).total_seconds() / 3600

def keyword_score(title: str, summary: str) -> int:
    text = (title + " " + summary).lower()
    return sum(1 for kw in HIGH_VALUE_KEYWORDS if kw.lower() in text)

def deduplicate(articles: list) -> list:
    """Remove near-duplicate titles using simple hash on normalized title."""
    seen = set()
    unique = []
    for a in articles:
        key = hashlib.md5(
            re.sub(r'\W+', '', a['title'].lower()).encode()
        ).hexdigest()[:12]
        if key not in seen:
            seen.add(key)
            unique.append(a)
    return unique

# ─────────────────────────────────────────────
#  CORE PIPELINE
# ─────────────────────────────────────────────

def fetch_all_feeds(max_age_hours: int = 36) -> list:
    """Fetch all feeds, filter to recent articles."""
    articles = []
    stats = {"fetched": 0, "skipped": 0, "errors": 0}

    for category, feeds in SOURCES.items():
        for url, source_name, quality in feeds:
            try:
                feed = feedparser.parse(url, request_headers={
                    'User-Agent': 'TechDigestBot/1.0 (+https://github.com)'
                })
                fetched_count = 0
                for entry in feed.entries[:20]:
                    pub_dt = parse_date(entry)
                    age = hours_ago(pub_dt)

                    if age > max_age_hours:
                        stats["skipped"] += 1
                        continue

                    title = clean_html(entry.get('title', 'No title'))
                    summary = clean_html(entry.get('summary', entry.get('description', '')))
                    link = entry.get('link', '#')

                    # Compute composite score
                    recency_score = max(0, 5 - (age / 8))  # 0–5, decays every 8h
                    kw_score = keyword_score(title, summary)
                    total_score = (quality * 1.5) + recency_score + kw_score

                    articles.append({
                        'title': title,
                        'link': link,
                        'summary': summary[:600],
                        'category': category,
                        'source': source_name,
                        'published': pub_dt,
                        'score': round(total_score, 2),
                        'age_hours': round(age, 1),
                    })
                    fetched_count += 1
                    stats["fetched"] += 1

            except Exception as e:
                stats["errors"] += 1
                print(f"  [WARN] Failed to fetch {source_name}: {e}")

    print(f"\n📊 Feed stats: {stats['fetched']} articles fetched, "
          f"{stats['skipped']} too old, {stats['errors']} feed errors")
    return articles

def select_top_articles(articles: list, per_category: int = 5, global_top: int = 3) -> dict:
    """
    Returns a dict with:
      - 'highlights': top N articles across ALL categories
      - per-category lists
    """
    deduped = deduplicate(articles)
    deduped.sort(key=lambda x: x['score'], reverse=True)

    highlights = deduped[:global_top]
    by_category = defaultdict(list)

    for a in deduped:
        cat = a['category']
        if len(by_category[cat]) < per_category:
            by_category[cat].append(a)

    return {
        'highlights': highlights,
        'by_category': dict(by_category),
        'total_collected': len(deduped),
    }

# ─────────────────────────────────────────────
#  DIGEST GENERATION
# ─────────────────────────────────────────────

def format_article(article: dict, index: int = None, show_score: bool = False) -> str:
    """Format a single article as Markdown."""
    idx_str = f"**{index}.** " if index else "- "
    age_str = f"{article['age_hours']}h ago"
    score_str = f" · score: {article['score']}" if show_score else ""

    lines = [
        f"{idx_str}**[{article['title']}]({article['link']})**",
        f"  `{article['source']}` · {age_str}{score_str}",
    ]
    if article['summary']:
        truncated = article['summary'][:280]
        if len(article['summary']) > 280:
            truncated += "…"
        lines.append(f"  {truncated}")
    lines.append("")
    return "\n".join(lines)

def generate_digest(data: dict) -> str:
    today = datetime.date.today()
    weekday = today.strftime("%A")
    date_str = today.strftime("%B %d, %Y")

    md = []
    md.append(f"# 🌅 Tech Digest — {weekday}, {date_str}")
    md.append(f"\n> Auto-generated daily briefing · {data['total_collected']} articles collected\n")
    md.append("---\n")

    # ── Top Highlights ──────────────────────────────────────────
    md.append("## 🔥 Top Highlights\n")
    md.append("> The highest-signal stories across all categories today.\n")
    for i, article in enumerate(data['highlights'], 1):
        md.append(f"**{i}. [{article['title']}]({article['link']})**")
        md.append(f"*{article['category']} · {article['source']} · {article['age_hours']}h ago*")
        if article['summary']:
            md.append(f"\n{article['summary'][:320]}…\n")
        md.append("")

    md.append("---\n")

    # ── Per-Category Sections ────────────────────────────────────
    category_order = [
        "⚙️ Software Engineering",
        "🤖 AI & Machine Learning",
        "🔐 Cybersecurity",
        "🌐 General Tech & Shifts",
    ]

    for cat in category_order:
        articles = data['by_category'].get(cat, [])
        if not articles:
            continue
        md.append(f"## {cat}\n")
        for i, article in enumerate(articles, 1):
            md.append(format_article(article, index=i))

        md.append("---\n")

    # ── Footer ───────────────────────────────────────────────────
    md.append(f"\n*Generated at {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')} · "
              f"Sources: {sum(len(v) for v in SOURCES.values())} feeds across 4 categories*")

    return "\n".join(md)

# ─────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────

def main():
    print("🚀 Starting Tech Digest Pipeline...")
    print(f"📅 Date: {datetime.date.today()}")
    print(f"📡 Configured sources: {sum(len(v) for v in SOURCES.values())} feeds\n")

    articles = fetch_all_feeds(max_age_hours=36)

    if not articles:
        print("⚠️  No articles fetched. Check your internet connection or feed URLs.")
        return

    data = select_top_articles(articles, per_category=5, global_top=3)
    digest = generate_digest(data)

    # Write to file
    output_path = os.environ.get("DIGEST_OUTPUT", "digest.md")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(digest)

    print(f"\n✅ Digest written to {output_path}")
    print(f"📰 Top highlights: {len(data['highlights'])}")
    print(f"📂 Categories covered: {list(data['by_category'].keys())}")
    print("\n--- PREVIEW (first 40 lines) ---")
    preview_lines = digest.split("\n")[:40]
    print("\n".join(preview_lines))

if __name__ == "__main__":
    main()