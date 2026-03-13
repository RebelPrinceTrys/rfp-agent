import anthropic
import smtplib
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
        system="Find health conferences with open calls for proposals, abstracts, RFPs, or oral/poster submissions. Only use URLs returned by your search tool. Never guess or invent URLs.",
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

Format your response in two sections:

SECTION 1 — OPEN NOW
List only conferences with submission windows currently open or opening within 60 days.
For each: conference name, organization, deadline, submission type, and URL.

SECTION 2 — PRIORITY ORGANIZATIONS STATUS
For each of the four priority organizations (GLMA, ASRM, WPATH, USPATH), confirm whether you found an open submission window or not. One line each."""
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

def send_email(summary, verified_urls):
    today = datetime.now().strftime("%B %d, %Y")
    url_list = "\n".join([f"• {u['title']}\n  {u['url']}" for u in verified_urls])

    body = f"""Conference RFP Tracker — {today}

=============================================
RESULTS
=============================================
{summary}

=============================================
ALL VERIFIED URLS (cross-check against summary)
=============================================
{url_list}

---
Any URL in the summary not appearing in the verified list above should be treated as unconfirmed.
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
    send_email(summary, verified_urls)
    print("Email sent successfully.")
else:
    print("No results found.")
