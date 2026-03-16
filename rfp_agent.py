import anthropic
import smtplib
import urllib.request
import time
from email.mime.text import MIMEText
import os
from datetime import datetime

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

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
            return response.read().decode("utf-8", errors="ignore")[:3000]
    except Exception as e:
        return f"Could not fetch page: {e}"

def run_agent():
    today = datetime.now().strftime("%B %d, %Y")

    # Fetch all priority pages with plain Python — zero API calls
    print("Fetching priority org pages directly...")
    priority_content = ""
    for name, url in PRIORITY_PAGES:
        print(f"  Fetching {name}...")
        content = fetch_page(url)
        time.sleep(2)  # polite pause between page fetches
        priority_content += f"\n\n--- {name} ({url}) ---\n{content}"

    # Now make exactly ONE API call that does everything
    print("Running single Claude analysis...")
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1000,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        system=f"Today is {today}. You help track conference submission deadlines. Only report opportunities with deadlines strictly after {today}. Never report expired deadlines. For priority organizations, base your answer only on the page content provided. For other conferences, use web search.",
        messages=[{
            "role": "user",
            "content": f"""Today is {today}.

PART 1 — PRIORITY ORGANIZATIONS (read the page content below, do not search for these):
For each organization, state in 1-2 sentences: is there a currently open submission window? If yes, what is the deadline and submission type? If no, what is the current status?

{priority_content}

PART 2 — BROADER SEARCH:
Now search the web for other LGBTQ health, trans health, and reproductive medicine conferences with submission windows currently open or opening within 60 days. Exclude GLMA, ASRM, WPATH, and USPATH. Only include deadlines after {today}. List conference name, deadline, submission type, and URL."""
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
    url_list = "\n".join(verified_urls) if verified_urls else "None returned."

    body = f"""Conference RFP Tracker — {today}

Priority organizations checked by direct page visit (GLMA, ASRM, WPATH, USPATH).
Broader results found via web search.

=============================================
FULL RESULTS
=============================================
{summary}

=============================================
VERIFIED URLs FROM WEB SEARCH
=============================================
{url_list}

---
Priority org results are based on live page content fetched today.
Web search results should be cross-checked against the URLs above.
"""

    msg = MIMEText(body)
    msg["Subject"] = f"Conference RFP Tracker — {today}"
    msg["From"] = os.environ["EMAIL_FROM"]
    msg["To"] = os.environ["EMAIL_TO"]
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(os.environ["EMAIL_FROM"], os.environ["GMAIL_APP_PASSWORD"])
        server.send_message(msg)

summary, verified_urls = run_agent()
if summary:
    send_email(summary, verified_urls)
    print("Email sent successfully.")
else:
    print("No results found.")
