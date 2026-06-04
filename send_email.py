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
      font-family: Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      background-color: #eef2f7;
      color: #182026;
    }}
    .wrapper {{
      width: 100%;
      padding: 24px 0;
    }}
    .container {{
      max-width: 760px;
      margin: 0 auto;
      background-color: #ffffff;
      border-radius: 18px;
      box-shadow: 0 24px 64px rgba(15, 23, 42, 0.12);
      overflow: hidden;
    }}
    .header {{
      padding: 32px 40px 20px;
      background: linear-gradient(135deg, #1f67ff 0%, #47b5ff 100%);
      color: #ffffff;
    }}
    .header h1 {{
      margin: 0;
      font-size: 28px;
      letter-spacing: -0.03em;
    }}
    .header p {{
      margin: 12px 0 0;
      color: rgba(255, 255, 255, 0.88);
      font-size: 15px;
      line-height: 1.6;
    }}
    .content {{
      padding: 32px 40px 40px;
      line-height: 1.7;
    }}
    h1 {{
      color: #102a43;
      font-size: 24px;
      margin: 24px 0 12px;
    }}
    h2 {{
      color: #0f172a;
      font-size: 19px;
      margin: 20px 0 8px;
      border-left: 4px solid #1f67ff;
      padding-left: 12px;
    }}
    p {{
      color: #334155;
      margin: 10px 0;
      font-size: 15px;
    }}
    a {{
      color: #1f67ff;
      text-decoration: none;
    }}
    a:hover {{
      text-decoration: underline;
    }}
    hr {{
      border: none;
      border-top: 1px solid #d9e2ec;
      margin: 28px 0;
    }}
    blockquote {{
      margin: 0 0 18px;
      padding: 16px 20px;
      border-left: 4px solid #1f67ff;
      background-color: #f0f4ff;
      color: #475569;
      font-style: italic;
    }}
    code {{
      background: #f1f5f9;
      padding: 2px 6px;
      border-radius: 4px;
      font-family: 'Courier New', monospace;
      font-size: 13px;
    }}
    .footer {{
      margin-top: 30px;
      font-size: 13px;
      color: #667085;
      text-align: center;
    }}
  </style>
</head>
<body>
  <div class="wrapper">
    <div class="container">
      <div class="header">
        <h1>Tech Digest</h1>
        <p>Curated morning briefing for software engineers. Insights, context, and impact in one concise note.</p>
      </div>
      <div class="content">
{body_html}
      </div>
      <div class="footer">
        Delivered automatically by GitHub Actions · Update your settings in the workflow if you want to pause delivery.
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
