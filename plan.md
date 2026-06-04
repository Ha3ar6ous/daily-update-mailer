# Improvement Plan for Daily Update Mailer

This plan focuses on the specific enhancements requested for the news aggregation pipeline: remove the Cybersecurity section, expand source collection, sharpen scoring, create a professional email format, and integrate LLM-powered summaries with the Groq API.

## 1. Consolidate categories and remove Cybersecurity

### 1.1 Remove Cybersecurity as a separate section

- Collapse the current `🔐 Cybersecurity` category into broader topic categories.
- Recommended final category structure:
  - `⚙️ Software Engineering`
  - `🤖 AI & Machine Learning`
  - `🌐 General Tech & Shifts`
- Benefit: simpler digest structure and stronger emphasis on top-priority tech news.

### 1.2 Rebalance feed allocation

- Redistribute existing cybersecurity feeds into `General Tech` or `AI & Machine Learning` where they fit.
- Keep the digest lean with the most important stories, not every niche security alert.

## 2. Expand source collection

### 2.1 Add authoritative high-signal sources

- Expand `SOURCES` with additional high-quality feeds in the remaining categories, such as:
  - `InfoQ`, `Dev.to`, `The Register`, `IEEE Spectrum`, `MIT Technology Review`, `VentureBeat`, `Bloomberg Technology`, `Fast Company`, `GitHub Blog`, `AWS News Blog`, `Microsoft Dev Blog`.
- Increase the number of AI and general tech feeds for broader signal capture.

### 2.2 Keep source quality ratings strict

- Add new feeds with a `quality_score` only if they consistently publish major news and analysis.
- Keep the source score range 1–5 and bias toward established editorial or research publishers.

## 3. Improve weight logic to prioritize most important news only

### 3.1 Refine score components for precision

- Use a multi-factor score formula:
  - source quality weight: 40–50%
  - recency weight: 25–30%
  - keyword relevance weight: 15–20%
  - content signal boost: 10–15%
- Make weights configurable in a small config object rather than hard-coded constants.

### 3.2 Upgrade scoring logic

- Improve the recency model with a smooth exponential decay instead of linear truncation.
- Use keyword matching on title, summary, and content to add relevance boosts for high-signal terms.
- Include source confidence penalties for low-quality or noisy feeds.

### 3.3 Enhance selection and filtering

- Only publish articles above a defined score threshold, not just the top N per category.
- Prefer a smaller digest of highly important stories over a larger digest of lower-value items.
- Keep the top highlights section focused on the best 3–5 stories overall.

### 3.4 Improve deduplication and uniqueness

- Deduplicate using title + normalized link + summary fingerprints.
- Filter out near-duplicates and reposts from syndicated feeds.
- Ensure the digest contains unique, clearly distinct news items.

## 4. Improve digest generation and email formatting

### 4.1 Create a professional email layout

- Replace the current dark, “vibecoded” style with a clean, minimal business newsletter design.
- Use a white/light container with well-defined sections, readable typography, and subtle accent colors.
- Include a polished header, section dividers, and a concise footer with source attribution.

### 4.2 Improve the digest structure

- Email should include:
  - subject line with date and a concise theme
  - top highlights section with 3–5 premium stories
  - category-specific sections with 3–4 stories each
  - article metadata: source, publish time, and score signal
  - concise explanations for why each story matters

### 4.3 Use HTML email best practices

- Embed a responsive, inline-style friendly HTML template.
- Ensure the email renders well across popular clients by avoiding advanced CSS.
- Include a plaintext fallback version for compatibility.

## 5. Add LLM-powered relevance summaries via Groq API

### 5.1 Integrate Groq API summarization

- Add a new module or helper for calling the Groq API.
- For each selected article, request a short explanatory summary that answers:
  - What is the core news?
  - Why does it matter?
  - Who is affected or what is changing?
- Use the API key from environment variables or workflow secrets.

### 5.2 Use summaries in the email digest

- Add a `Relevant Explanation` block under each article item.
- Keep summaries concise (2–3 sentences) and focused on the main takeaway.
- Ensure the digest is still readable at a glance, with summaries enhancing context rather than overloading it.

### 5.3 Optimize for cost and reliability

- Cache or store summaries for duplicate articles to avoid repeated LLM calls.
- Use batch summarization where possible to reduce requests.
- Add fallback copy generation when the Groq API fails, so the digest still sends with a plain summary.

## 6. Suggested implementation priorities

1. Remove Cybersecurity section and rebalance categories.
2. Expand high-quality source collection and maintain strict quality scores.
3. Refine scoring weights and selection thresholds to surface only the highest-value stories.
4. Build a clean HTML email template and add a professional layout.
5. Integrate Groq API to generate short explanatory summaries for each selected item.

## 7. Required project updates

- `daily_digest.py`:
  - update category structure
  - expand feed list
  - implement enhanced scoring rules
  - deduplicate more rigorously
- `send_email.py`:
  - replace the current HTML template with a professional newsletter template
  - preserve plain-text fallback
- New module `llm_summary.py` or similar:
  - manage Groq API calls
  - cache generated explanations
  - provide quality-controlled output
- Configuration:
  - support Groq API key via `GROQ_API_KEY`
  - support score weight settings and digest thresholds

## 8. Outcome

After these changes, the project will deliver a sharper, more business-ready daily briefing: strong sources, clean presentation, fewer noise stories, and an LLM-powered summary layer that lets readers understand the key news without clicking every link.
