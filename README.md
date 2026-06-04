# Daily Update Mailer

A personal daily news briefing pipeline for software engineers. It aggregates high-signal RSS/Atom feeds, ranks stories by source quality, recency, and relevance, enriches them with Groq-powered summaries, generates a polished Markdown digest, and optionally sends it as a styled HTML email.

## Overview

This repository includes:

- `daily_digest.py`: collects and filters feed entries, scores and deduplicates articles, attaches LLM summaries, and writes the digest to `digest.md`.
- `llm_summary.py`: calls the Groq API to generate concise, context-aware summaries for selected stories and caches results locally.
- `send_email.py`: converts the generated Markdown digest into HTML email content and sends it through Gmail SMTP.
- `.github/workflows/daily-digest.yml`: runs the pipeline on a schedule and can also run manually.

## Key Features

- Aggregates curated sources across:
  - `⚙️ Software Engineering`
  - `🤖 AI & Machine Learning`
  - `🌐 General Tech & Shifts`
- Prioritizes stories by source quality, recency, and keyword relevance.
- Removes duplicate coverage across feeds.
- Enriches chosen articles with Groq LLM summaries.
- Produces a professional HTML newsletter for email delivery.
- Supports local testing and GitHub Actions automation.

## Requirements

- Python 3.11+
- `feedparser`
- `httpx`
- `python-dateutil`

Install dependencies:

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

## Local Testing

### 1. Generate the digest locally

```powershell
python daily_digest.py
```

This creates or updates `digest.md` in the repository root.

### 2. Test the email sender locally

Set your Gmail credentials and recipient, then run:

```powershell
$env:GMAIL_USERNAME = "your@gmail.com"
$env:GMAIL_PASSWORD = "your_app_password"
$env:RECIPIENT_EMAIL = "recipient@example.com"
python send_email.py
```

If `RECIPIENT_EMAIL` is not set, the digest is sent to `GMAIL_USERNAME`.

### 3. Test both steps in one command

```powershell
python daily_digest.py
python send_email.py
```

### Optional output path

To use a different digest filename:

```powershell
$env:DIGEST_OUTPUT = "my_digest.md"
python daily_digest.py
python send_email.py
```

## Groq Integration

The project uses `llm_summary.py` to enrich selected articles with Groq-generated summaries.

### Required GitHub secrets

Add the following repository secrets in GitHub:

- `GROQ_API_KEY` — your Groq API key
- `GROQ_MODEL` — optional model name (default: `groq-llama2-mini`)
- `GROQ_API_URL` — optional endpoint URL (default is derived from the model name)

### Local environment variables

For local testing, set the same values in your shell:

```powershell
$env:GROQ_API_KEY = "your_groq_api_key"
$env:GROQ_MODEL = "groq-llama2-mini"
$env:GROQ_API_URL = "https://api.groq.com/v1/models/groq-llama2-mini/outputs"
```

### How it works

- `daily_digest.py` imports `explain_article` from `llm_summary.py`.
- `llm_summary.py` builds a prompt from each article and calls Groq.
- Successful summaries are cached to `summary_cache.json`.
- If the Groq API is unavailable, the pipeline falls back to the source summary text.

## GitHub Actions Setup

The workflow `.github/workflows/daily-digest.yml` runs the project daily at `02:00 UTC` and can also be triggered manually.

### Required secrets for the workflow

- `GROQ_API_KEY`
- `GROQ_MODEL` (optional)
- `GROQ_API_URL` (optional)
- `GMAIL_USERNAME` — Gmail address used to send mail
- `GMAIL_PASSWORD` — Gmail app password
- `RECIPIENT_EMAIL` — delivery address

### Notes for GitHub Actions

- `digest.md` is now treated as generated output and should not be committed back automatically.
- The workflow only sends email when SMTP credentials are present.

## Configuration

### Adjust sources

Edit `SOURCES` in `daily_digest.py` to add or remove feeds. Each source is defined as:

```python
("feed_url", "display_name", quality_score)
```

### Tune relevance

Update `HIGH_VALUE_KEYWORDS` in `daily_digest.py` to favor the topics you care about.

### Change email style

Update `build_email_html()` in `send_email.py` to adjust colors, layout, and branding.

## Troubleshooting

- If the digest is empty, check network connectivity and feed URLs.
- If Groq summaries do not appear, verify `GROQ_API_KEY` and the API endpoint.
- If email sending fails, confirm Gmail app-password access and environment variables.
- For local debugging, run `python daily_digest.py` and `python send_email.py` separately.

## Notes

- The digest is generated automatically, but it is safe to run locally for testing before workflow deployment.
- `summary_cache.json` stores Groq responses locally so repeated summaries do not re-run the API call.

## License

This repository does not include a license file. Add one if you want to publish or share the code publicly.
