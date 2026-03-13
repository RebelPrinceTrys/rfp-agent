import anthropic
import smtplib
import time
from email.mime.text import MIMEText
import os
from datetime import datetime

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

PRIORITY_ORGS = [
    ("GLMA", "glma.org", "GLMA conference abstracts submissions proposals"),
    ("ASRM", "asrm.org", "ASRM annual meeting abstract submissions"),
    ("WPATH", "wpath.org", "WPATH symposium abstract submissions proposals"),
    ("USPATH", "uspath.org", "USPATH conference abstract submissions proposals"),
]

def search_for_rfps():
    today = datetime.now().strftime("%B %d, %Y")

    priority_text = "\n".join([
        f"- {name} ({site}): '{query}'"
        for name, site, query in PRIORITY_ORGS
    ])

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1000,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        system="Find health conferences with open calls for proposals, abstracts, RFPs, or oral/poster submissions. Only report windows open now or within 60 days. Only use URLs returned by your search tool. Never guess or invent URLs.",
        messages=[{
            "role": "user",
            "content": f"""Today is {today}.

Search these priority organizations first. Note explicitly if nothing is open:
{priority_text}

Then search broadly for:
- LGBTQ health conferences open RFPs calls for abstracts
- Queer trans health symposium submissions open
- Sexual gender minority health conference CFP
- Reproductive medicine conference abstract submissions

For each result: conference name, organization, deadline, submission type. No URLs in summary."""
        }]
    )

    verified_urls = []
    summary = None

    for block in response.content:
        if block.type == "web_search_tool_result":
            for item in (block.content or []):
                if hasattr(item, "url") and item.url:
                    title = getattr(item, "title", item.url)
                    verified_urls.append({"title": title, "url": item.url})
        if block.type == "text":
            summary = block.text

    return summary, verified_urls

def triage_urls(verified_urls, today):
    if not verified_urls:
        return "No URLs were returned by the search engine."

    trimmed = verified_urls[:10]
    url_list = "\n".join([f"- {u['title']}: {u['url']}" for u in trimmed])

    print("Pausing before triage step...")
    time.sleep(60)

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1000,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        system="Visit each URL and check if it has an actively open submission window. Only mark OPEN if clearly confirmed.",
        messages=[{
            "role": "user",
            "content": f"""Today is {today}. Check each URL for open submission windows (proposals, abstracts, oral, poster). Sort into:

OPEN NOW: currently active (include deadline and submission type)
NOT OPEN: closed, not yet announced, or unclear

URLs:
{url_list}"""
        }]
    )

    triage_text = ""
    for block in response.content:
        if block.type == "text":
            triage_text = block.text

    return triage_text

def send_email(triage_summary, verified_urls, summary):
    today = datetime.now().strftime("%B %d, %Y")
    url_list = "\n".join([f"• {u['title']}\n  {u['url']}" for u in verified_urls])

    body = f"""Conference RFP Tracker — {today}

PRIORITY ORGANIZATIONS CHECKED:
- GLMA (glma.org)
- ASRM (asrm.org)
- WPATH (wpath.org)
- USPATH (uspath.org)

=============================================
ACTION NEEDED — OPEN SUBMISSIONS
=============================================
{triage_summary}

=============================================
ALL VERIFIED URLS
=============================================
{url_list}

=============================================
FULL AI SUMMARY
=============================================
{summary}

---
Any URL in the summary not in the verified list should be treated as unconfirmed.
"""

    msg = MIMEText(body)
    msg["Subject"] = f"Conference RFP Tracker — {today}"
    msg["From"] = os.environ["EMAIL_FROM"]
    msg["To"] = os.environ["EMAIL_TO"]
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(os.environ["EMAIL_FROM"], os.environ["GMAIL_APP_PASSWORD"])
        server.send_message(msg)

today = datetime.now().strftime("%B %d, %Y")
summary, verified_urls = search_for_rfps()
if summary:
    triage_summary = triage_urls(verified_urls, today)
    send_email(triage_summary, verified_urls, summary)
    print("Email sent successfully.")
else:
    print("No results found.")
