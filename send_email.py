"""
send_email.py — Sends the digest.md as a styled HTML email via Gmail SMTP.
Reads credentials from environment variables (set as GitHub Secrets).
"""

import os
import smtplib
import datetime
import re
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def md_to_html(md: str) -> str:
    """
    Minimal Markdown → HTML converter for our specific digest format.
    No external deps needed.
    """
    lines = md.split("\n")
    html_lines = []
    in_blockquote = False

    for line in lines:
        # Blockquote
        if line.startswith("> "):
            if not in_blockquote:
                html_lines.append("<blockquote>")
                in_blockquote = True
            html_lines.append(f"<p>{line[2:]}</p>")
            continue
        else:
            if in_blockquote:
                html_lines.append("</blockquote>")
                in_blockquote = False

        # H1
        if line.startswith("# "):
            html_lines.append(f"<h1>{line[2:]}</h1>")
        # H2
        elif line.startswith("## "):
            html_lines.append(f"<h2>{line[3:]}</h2>")
        # HR
        elif line.strip() == "---":
            html_lines.append("<hr>")
        # Inline markdown inside paragraph
        else:
            # Bold+link: **[text](url)**
            line = re.sub(r'\*\*\[(.+?)\]\((.+?)\)\*\*',
                          r'<strong><a href="\2">\1</a></strong>', line)
            # Bold: **text**
            line = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', line)
            # Italic: *text*
            line = re.sub(r'\*(.+?)\*', r'<em>\1</em>', line)
            # Inline code: `text`
            line = re.sub(r'`(.+?)`', r'<code>\1</code>', line)
            # Plain link: [text](url)
            line = re.sub(r'\[(.+?)\]\((.+?)\)', r'<a href="\2">\1</a>', line)

            if line.strip():
                html_lines.append(f"<p>{line}</p>")
            else:
                html_lines.append("<br>")

    if in_blockquote:
        html_lines.append("</blockquote>")

    return "\n".join(html_lines)


def build_email_html(digest_md: str) -> str:
    body = md_to_html(digest_md)
    today = datetime.date.today().strftime("%B %d, %Y")

    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Tech Digest {today}</title>
<style>
  body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: #0f0f0f;
    color: #e0e0e0;
    margin: 0; padding: 20px;
    line-height: 1.7;
  }}
  .container {{
    max-width: 720px;
    margin: 0 auto;
    background: #1a1a1a;
    border-radius: 12px;
    padding: 32px 40px;
    border: 1px solid #2a2a2a;
  }}
  h1 {{
    font-size: 26px;
    color: #f0c040;
    margin-bottom: 8px;
    border-bottom: 2px solid #333;
    padding-bottom: 10px;
  }}
  h2 {{
    font-size: 19px;
    color: #60b0ff;
    margin-top: 28px;
    margin-bottom: 12px;
    border-left: 4px solid #60b0ff;
    padding-left: 10px;
  }}
  p {{ margin: 6px 0 10px 0; color: #ccc; }}
  a {{ color: #7ec8e3; text-decoration: none; }}
  a:hover {{ text-decoration: underline; }}
  strong {{ color: #fff; }}
  code {{
    background: #2a2a2a;
    padding: 2px 6px;
    border-radius: 4px;
    font-family: 'Fira Code', monospace;
    font-size: 13px;
    color: #90ee90;
  }}
  hr {{
    border: none;
    border-top: 1px solid #333;
    margin: 24px 0;
  }}
  blockquote {{
    border-left: 3px solid #555;
    margin: 0;
    padding: 4px 16px;
    color: #999;
    font-style: italic;
  }}
  .footer {{
    margin-top: 32px;
    font-size: 12px;
    color: #555;
    text-align: center;
  }}
</style>
</head>
<body>
<div class="container">
{body}
<div class="footer">
  Tech Digest Pipeline · Delivered by GitHub Actions · Unsubscribe anytime by disabling the workflow
</div>
</div>
</body>
</html>
"""


def send_digest_email():
    # Read from environment
    smtp_user = os.environ.get("GMAIL_USERNAME")
    smtp_pass = os.environ.get("GMAIL_PASSWORD")
    recipient = os.environ.get("RECIPIENT_EMAIL", smtp_user)
    digest_path = os.environ.get("DIGEST_OUTPUT", "digest.md")

    if not smtp_user or not smtp_pass:
        print("⚠️  GMAIL_USERNAME or GMAIL_PASSWORD not set. Skipping email.")
        return

    # Read digest
    if not os.path.exists(digest_path):
        print(f"❌ Digest file not found at {digest_path}")
        return

    with open(digest_path, "r", encoding="utf-8") as f:
        digest_md = f.read()

    today = datetime.date.today().strftime("%B %d, %Y")
    subject = f"🌅 Tech Digest — {today}"

    # Build message
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = smtp_user
    msg["To"] = recipient

    # Plain text fallback
    msg.attach(MIMEText(digest_md, "plain"))
    # HTML version
    html_body = build_email_html(digest_md)
    msg.attach(MIMEText(html_body, "html"))

    # Send via Gmail SMTP
    print(f"📧 Sending digest to {recipient}...")
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, recipient, msg.as_string())
        print("✅ Email sent successfully!")
    except Exception as e:
        print(f"❌ Failed to send email: {e}")
        raise


if __name__ == "__main__":
    send_digest_email()