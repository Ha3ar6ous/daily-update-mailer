"""
send_email.py — Sends the generated digest as a polished HTML newsletter via Gmail SMTP.
Uses environment variables for credentials and supports plaintext fallback.
"""

import os
import datetime
import smtplib
import re
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def md_to_html(md: str) -> str:
    lines = md.splitlines()
    html_lines = []
    in_blockquote = False

    for line in lines:
        if line.startswith("> "):
            if not in_blockquote:
                html_lines.append("<blockquote>")
                in_blockquote = True
            html_lines.append(f"<p>{line[2:]}</p>")
            continue
        if in_blockquote:
            html_lines.append("</blockquote>")
            in_blockquote = False

        if line.startswith("# "):
            html_lines.append(f"<h1>{line[2:].strip()}</h1>")
        elif line.startswith("## "):
            html_lines.append(f"<h2>{line[3:].strip()}</h2>")
        elif line.strip() == "---":
            html_lines.append("<hr />")
        else:
            text = line
            text = re.sub(r"\*\*\[(.+?)\]\((.+?)\)\*\*", r"<strong><a href=\"\2\">\1</a></strong>", text)
            text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
            text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)
            text = re.sub(r"`(.+?)`", r"<code>\1</code>", text)
            text = re.sub(r"\[(.+?)\]\((.+?)\)", r"<a href=\"\2\">\1</a>", text)

            if text.strip():
                html_lines.append(f"<p>{text}</p>")
            else:
                html_lines.append("<div style=\"margin: 12px 0;\"></div>")

    if in_blockquote:
        html_lines.append("</blockquote>")

    return "\n".join(html_lines)


def build_email_html(digest_md: str) -> str:
    body_html = md_to_html(digest_md)
    today = datetime.date.today().strftime("%B %d, %Y")
    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Tech Digest — {today}</title>
  <style>
    body {{
      margin: 0;
      padding: 0;
      font-family: 'Segoe UI', Roboto, -apple-system, BlinkMacSystemFont, sans-serif;
      background-color: #f5f7fa;
      color: #1f2937;
    }}
    .wrapper {{
      width: 100%;
      padding: 16px;
    }}
    .container {{
      max-width: 800px;
      margin: 0 auto;
      background-color: #ffffff;
      border-radius: 12px;
      box-shadow: 0 10px 40px rgba(0, 0, 0, 0.08);
      overflow: hidden;
    }}
    .header {{
      padding: 40px 36px 28px;
      background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%);
      color: #ffffff;
      border-bottom: 6px solid #1e40af;
    }}
    .header h1 {{
      margin: 0 0 8px;
      font-size: 32px;
      font-weight: 700;
      letter-spacing: -0.5px;
    }}
    .header p {{
      margin: 0;
      color: rgba(255, 255, 255, 0.9);
      font-size: 14px;
      line-height: 1.5;
    }}
    .content {{
      padding: 36px;
      line-height: 1.8;
    }}
    .section {{
      margin-bottom: 32px;
    }}
    .section h2 {{
      color: #0f172a;
      font-size: 21px;
      font-weight: 700;
      margin: 0 0 20px;
      padding-bottom: 12px;
      border-bottom: 3px solid #3b82f6;
    }}
    .article-item {{
      background: #f8fafc;
      border-left: 4px solid #3b82f6;
      padding: 20px;
      margin-bottom: 18px;
      border-radius: 6px;
      transition: all 0.2s ease;
    }}
    .article-item:hover {{
      background: #f0f4f8;
      border-left-color: #1e40af;
    }}
    .article-number {{
      display: inline-block;
      background: #3b82f6;
      color: #ffffff;
      width: 28px;
      height: 28px;
      border-radius: 50%;
      text-align: center;
      line-height: 28px;
      font-weight: 700;
      font-size: 13px;
      margin-right: 10px;
    }}
    .article-title {{
      display: inline;
      font-size: 17px;
      font-weight: 700;
      color: #0f172a;
    }}
    .article-title a {{
      color: #1e3a8a;
      text-decoration: none;
      border-bottom: 2px solid transparent;
      transition: border 0.2s ease;
    }}
    .article-title a:hover {{
      border-bottom: 2px solid #3b82f6;
    }}
    .article-meta {{
      margin-top: 8px;
      font-size: 13px;
      color: #64748b;
      font-weight: 500;
    }}
    .article-meta span {{
      margin-right: 16px;
    }}
    .article-summary {{
      margin-top: 12px;
      padding: 12px 0 0;
      font-size: 14px;
      color: #374151;
      line-height: 1.6;
    }}
    strong {{
      color: #1f2937;
      font-weight: 600;
    }}
    a {{
      color: #1e3a8a;
      text-decoration: none;
    }}
    a:hover {{
      text-decoration: underline;
    }}
    hr {{
      border: none;
      border-top: 1px solid #e5e7eb;
      margin: 28px 0;
    }}
    blockquote {{
      margin: 0 0 20px;
      padding: 12px 16px;
      border-left: 4px solid #3b82f6;
      background-color: #eff6ff;
      color: #1e3a8a;
      font-style: italic;
      font-size: 14px;
    }}
    code {{
      background: #f3f4f6;
      padding: 2px 6px;
      border-radius: 3px;
      font-family: 'Monaco', 'Courier New', monospace;
      font-size: 13px;
      color: #374151;
    }}
    .footer {{
      margin-top: 32px;
      padding-top: 20px;
      border-top: 1px solid #e5e7eb;
      font-size: 12px;
      color: #6b7280;
      text-align: center;
    }}
  </style>
</head>
<body>
  <div class="wrapper">
    <div class="container">
      <div class="header">
        <h1>📰 Tech Digest</h1>
        <p>Enterprise-grade intelligence briefing for software engineering leaders. Curated insights from 30+ premium sources.</p>
      </div>
      <div class="content">
{body_html}
      </div>
      <div class="footer">
        <p>Automated intelligence digest · Delivered by GitHub Actions · Powered by Groq API</p>
        <p style="margin-top: 8px; font-size: 11px; color: #9ca3af;">Manage your subscription in the GitHub Actions workflow settings if you want to pause or modify delivery.</p>
      </div>
    </div>
  </div>
</body>
</html>
"""


def normalize_plaintext(md: str) -> str:
    text = re.sub(r"\*\*\[(.+?)\]\((.+?)\)\*\*", r"\1 (\2)", md)
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"\*(.+?)\*", r"\1", text)
    text = re.sub(r"\[(.+?)\]\((.+?)\)", r"\1 (\2)", text)
    return text


def send_digest_email():
    smtp_user = os.environ.get("GMAIL_USERNAME")
    smtp_pass = os.environ.get("GMAIL_PASSWORD")
    recipient = os.environ.get("RECIPIENT_EMAIL", smtp_user)
    digest_path = os.environ.get("DIGEST_OUTPUT", "digest.md")

    if not smtp_user or not smtp_pass:
        print("⚠️ GMAIL_USERNAME or GMAIL_PASSWORD not set. Skipping email.")
        return

    if not os.path.exists(digest_path):
        print(f"❌ Digest file not found at {digest_path}")
        return

    with open(digest_path, "r", encoding="utf-8") as reader:
        digest_md = reader.read()

    subject = f"🌅 Tech Digest — {datetime.date.today():%B %d, %Y}"
    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = smtp_user
    message["To"] = recipient

    plaintext = normalize_plaintext(digest_md)
    message.attach(MIMEText(plaintext, "plain"))
    message.attach(MIMEText(build_email_html(digest_md), "html"))

    print(f"📧 Sending digest to {recipient}...")
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(smtp_user, smtp_pass)
            smtp.sendmail(smtp_user, recipient, message.as_string())
        print("✅ Email sent successfully.")
    except Exception as exc:
        print(f"❌ Email send failed: {exc}")
        raise


if __name__ == "__main__":
    send_digest_email()
