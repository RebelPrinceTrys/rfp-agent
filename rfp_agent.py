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
        system="You are a research assistant finding LGBTQ health conferences with currently open calls for proposals (RFPs, CFPs, calls for abstracts). For each result you MUST include the direct URL. Only include conferences where submission windows are currently open or opening within 60 days. Never invent or guess URLs.",
        messages=[{
            "role": "user",
            "content": f"Today is {today}. Search for: LGBTQ health conferences with open RFPs or calls for proposals, queer health symposiums accepting abstracts, trans health conference calls for submissions, sexual and gender minority health conference CFPs. For each, list: conference name, hosting organization, deadline, what they want, and the direct submission URL. Only include future deadlines."
        }]
    )
    for block in response.content:
        if block.type == "text":
            return block.text
    return None

def send_email(body):
    today = datetime.now().strftime("%B %d, %Y")
    msg = MIMEText(body)
    msg["Subject"] = f"LGBTQ Health Conference RFPs — {today}"
    msg["From"] = os.environ["EMAIL_FROM"]
    msg["To"] = os.environ["EMAIL_TO"]
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(os.environ["EMAIL_FROM"], os.environ["GMAIL_APP_PASSWORD"])
        server.send_message(msg)

results = search_for_rfps()
if results:
    send_email(results)
    print("Email sent successfully.")
else:
    print("No results found.")
