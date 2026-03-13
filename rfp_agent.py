import anthropic
import smtplib
from email.mime.text import MIMEText
import os
from datetime import datetime

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

def search_for_rfps():
    today = datetime.now().strftime("%B %d, %Y")
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1000,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        system="You are a research assistant finding LGBTQ health conferences with currently open calls for proposals (RFPs, CFPs, calls for abstracts). Only report conferences whose submission windows are currently open or opening within 60 days. For each result, only include URLs that were returned directly by your web search tool. Never construct, guess, or infer URLs.",
        messages=[{
            "role": "user",
            "content": f"Today is {today}. Search for: LGBTQ health conferences with open RFPs or calls for proposals, queer health symposiums accepting abstracts, trans health conference calls for submissions, sexual and gender minority health conference CFPs. For each, list: conference name, hosting organization, deadline, and what they are looking for. Do not include any URLs in your summary — those will be listed separately."
        }]
    )

    verified_urls = []
    summary = None

    for block in response.content:
        if block.type == "web_search_tool_result":
            for item in (block.content or []):
                if hasattr(item, "url") and item.url:
                    title = getattr(item, "title", item.url)
                    verified_urls.append(f"• {title}\n  {item.url}")
        if block.type == "text":
            summary = block.text

    return summary, verified_urls

def send_email(summary, verified_urls):
    today = datetime.now().strftime("%B %d, %Y")

    url_section = "\n".join(verified_urls) if verified_urls else "No URLs were returned by the search engine."

    body = f"""LGBTQ Health Conference RFPs — {today}

VERIFIED URLS (returned directly by search engine — these are real):
{url_section}

---

AI SUMMARY (cross-check any links here against the verified list above):
{summary}

---
Any URL in the summary that does not appear in the verified list above should be treated as unconfirmed.
"""

    msg = MIMEText(body)
    msg["Subject"] = f"LGBTQ Health Conference RFPs — {today}"
    msg["From"] = os.environ["EMAIL_FROM"]
    msg["To"] = os.environ["EMAIL_TO"]
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(os.environ["EMAIL_FROM"], os.environ["GMAIL_APP_PASSWORD"])
        server.send_message(msg)

summary, verified_urls = search_for_rfps()
if summary:
    send_email(summary, verified_urls)
    print("Email sent successfully.")
else:
    print("No results found.")
