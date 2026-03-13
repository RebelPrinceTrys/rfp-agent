import anthropic
import smtplib
from email.mime.text import MIMEText
import os
from datetime import datetime

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

PRIORITY_ORGS = [
    ("GLMA", "glma.org", "GLMA annual conference abstracts submissions proposals"),
    ("ASRM", "asrm.org", "ASRM annual meeting abstract submissions oral poster"),
    ("WPATH", "wpath.org", "WPATH symposium abstract submissions call for proposals"),
    ("USPATH", "uspath.org", "USPATH conference abstract submissions call for proposals"),
]

def search_for_rfps():
    today = datetime.now().strftime("%B %d, %Y")

    priority_text = "\n".join([
        f"- {name} ({site}): Search specifically for '{query}'"
        for name, site, query in PRIORITY_ORGS
    ])

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1000,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        system="You are a research assistant finding health conferences with currently open calls for proposals, calls for abstracts, RFPs, oral and poster abstract submissions, or requests for abstracts. Only report conferences whose submission windows are currently open or opening within 60 days. For each result, only include URLs that were returned directly by your web search tool. Never construct, guess, or infer URLs.",
        messages=[{
            "role": "user",
            "content": f"""Today is {today}.

PRIORITY ORGANIZATIONS — search each of these specifically every time, regardless of whether their submission window is currently open. If nothing is open, note that explicitly so I know you checked:

{priority_text}

GENERAL SEARCH — also search broadly for:
- LGBTQ health conferences with open RFPs or calls for proposals
- Queer health symposiums accepting abstracts
- Trans health conference calls for submissions
- Sexual and gender minority health conference CFPs
- LGBTQ health conference oral abstract submissions
- LGBTQ health conference poster abstract submissions
- Reproductive medicine conference request for abstracts
- LGBTQ health conference symposium submissions open

For each result, list: conference name, hosting organization, deadline, and what they are looking for. Do not include any URLs in your summary — those will be listed separately."""
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

    url_list = "\n".join([f"- {u['title']}: {u['url']}" for u in verified_urls])

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1000,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        system="You are a careful research assistant. Your job is to visit URLs and determine whether each one has an actively open call for proposals, call for abstracts, request for abstracts, oral or poster submission window, or RFP right now. Be conservative: only mark something as OPEN if you can clearly confirm the submission window is currently active.",
        messages=[{
            "role": "user",
            "content": f"""Today is {today}. For each URL below, check whether there is a currently open submission window of any kind — including calls for proposals, calls for abstracts, requests for abstracts, oral submissions, or poster submissions. Sort them into two groups:

OPEN NOW: submission window is currently active
NOT OPEN: already closed, not yet announced, or unclear

URLs to check:
{url_list}

For each OPEN NOW item, include the deadline and what type of submission is being accepted. Be brief and factual."""
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

PRIORITY ORGANIZATIONS CHECKED THIS RUN:
- GLMA (glma.org)
- ASRM (asrm.org)
- WPATH (wpath.org)
- USPATH (uspath.org)

=============================================
ACTION NEEDED — OPEN SUBMISSIONS
=============================================
{triage_summary}

=============================================
ALL VERIFIED URLS (for your reference)
=============================================
{url_list}

=============================================
FULL AI SUMMARY
=============================================
{summary}

---
Any URL in the summary that does not appear in the verified list should be treated as unconfirmed.
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
