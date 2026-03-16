import anthropic
import smtplib
import urllib.request
from email.mime.text import MIMEText
import os
from datetime import datetime

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

# These pages are fetched directly every run, no search engine involved
PRIORITY_PAGES = [
    ("GLMA", "https://glma.org/guidelines_for_submitting_abst.php"),
    ("ASRM", "https://www.asrm.org/education/meetings-and-events/annual-meeting/call-for-abstracts/"),
    ("WPATH", "https://s2.goeshow.com/wpath/annual/2026/abstract_submission.cfm"),
    ("USPATH", "https://uspath.org/2026-conference/"),
]

def fetch_page(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as response:
            return response.read().decode("utf-8", errors="ignore")[:8000]
    except Exception as e:
        return f"Could not fetch page: {e}"

def check_priority_orgs():
    today = datetime.now().strftime("%B %d, %Y")
    results = []

    for name, url in PRIORITY_PAGES:
        print(f"Checking {name} directly...")
        content = fetch_page(url)

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=300,
            messages=[{
                "role": "user",
                "content": f"""Today is {today}. Here is the raw content of the {name} website page at {url}:

{content}

Based only on this page content, answer in 2-3 sentences:
1. Is there a currently open call for proposals, abstracts, or submissions? (Yes/No)
2. If yes: what is the deadline and what type of submission is being accepted?
3. If no: what is the current status (e.g. closed, not yet announced, past conference)?

Be factual and brief. Do not guess."""
            }]
        )

        summary = response.content[-1].text
        results.append(f"{name} ({url})\n{summary}")

    return "\n\n".join(results)

def search_broadly():
    today = datetime.now().strftime("%B %d, %Y")

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=800,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        system="Find health conferences with open calls for proposals, abstracts, RFPs, or oral/poster submissions. Today's date is important: only include opportunities with deadlines in the future. Never include expired deadlines. Only use URLs returned by your search tool.",
        messages=[{
            "role": "user",
            "content": f"""Today is {today}. Search for conferences beyond GLMA, ASRM, WPATH, and USPATH (those are already checked separately).

Search for:
- LGBTQ health conferences open calls for abstracts {today[:4]}
- Queer trans health symposium submissions open {today[:4]}
- Sexual gender minority health conference CFP {today[:4]}
- Reproductive medicine conference abstract submissions {today[:4]}

Only include opportunities where the deadline is after {today}. For each, list: conference name, organization, deadline, submission type, and URL. If you cannot confirm the deadline is in the future, do not include it."""
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

def send_email(priority_results, broad_summary, verified_urls):
    today = datetime.now().strftime("%B %d, %Y")
    url_list = "\n".join(verified_urls) if verified_urls else "None returned."

    body = f"""Conference RFP Tracker — {today}

=============================================
PRIORITY ORGANIZATIONS (checked directly)
=============================================
These four organizations were checked by visiting their websites directly today.

{priority_results}

=============================================
OTHER CONFERENCES (web search)
=============================================
{broad_summary}

=============================================
VERIFIED URLS FROM BROAD SEARCH
=============================================
{url_list}

---
Priority org results come from direct page fetches and are more reliable.
Broad search results should be cross-checked against the URLs listed above.
"""

    msg = MIMEText(body)
    msg["Subject"] = f"Conference RFP Tracker — {today}"
    msg["From"] = os.environ["EMAIL_FROM"]
    msg["To"] = os.environ["EMAIL_TO"]
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(os.environ["EMAIL_FROM"], os.environ["GMAIL_APP_PASSWORD"])
        server.send_message(msg)

today = datetime.now().strftime("%B %d, %Y")
print("Checking priority organizations directly...")
priority_results = check_priority_orgs()
print("Running broad search...")
broad_summary, verified_urls = search_broadly()
send_email(priority_results, broad_summary, verified_urls)
print("Email sent successfully.")
