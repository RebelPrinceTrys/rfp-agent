"""
ADHD Prioritizer — minimal-slice backend.

Takes a raw to-do list plus the user's chosen core values, asks Claude to
tag each task with a value, a "why", a consequence, a deadline read, and a
scored urgency/importance, then returns the list sorted by total score.

Run with:
    uvicorn app:app --reload
"""
import json
import os
from datetime import date, datetime, timedelta

import anthropic
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

app = FastAPI(title="ADHD Prioritizer")

TIME_BUCKETS = ["<=2min", "2-5min", "5-30min", "30-60min", ">60min"]

# Effort tiebreaker: quick tasks get a small boost so short, easy wins can
# nudge ahead of similarly-scored longer ones. Kept small on purpose so it
# never outweighs urgency or importance.
EFFORT_WEIGHT = {
    "<=2min": 10,
    "2-5min": 7,
    "5-30min": 4,
    "30-60min": 2,
    ">60min": 0,
}

CORE_VALUES = [
    "money",
    "reputation",
    "relationship",
    "ease",
    "fun",
    "family",
    "loyalty",
    "health and wellness",
]


class PrioritizeRequest(BaseModel):
    tasks: str  # one task per line
    values: list[str]


SYSTEM_PROMPT = f"""You help an ADHD adult triage their to-do list. ADHD brains
experience "time blending" (a huge list feels flat — paying the mortgage feels
as weighty as looking up gardening ideas) and respond to urgency, novelty, and
personal meaning far more than to a task's objective importance. Your job is
to give each task a concrete "why" tied to one of the user's stated core
values, a plain-language consequence if it's skipped, a realistic time
estimate, and numeric scores so the app can sort the list for them.

Today's date is {date.today().isoformat()}.

The user's core values (only use these, verbatim, as the "value" field):
{", ".join(CORE_VALUES)}

For EACH task in the user's list, return an object with:
- "task": the task text, lightly cleaned up but recognizable to the user
- "value": one value from the user's selected list that this task most
  directly serves. If none fit well, still pick the closest one — don't
  invent new values.
- "why": one short sentence tying the task to that value (e.g. "so your
  family keeps a stable home").
- "consequence": one short, concrete sentence on what happens if this is
  skipped or delayed. Be specific, not generic ("late fee added to next
  bill", not "bad things happen").
- "deadline_type": "none", "internal" (the user set it), or "external"
  (someone/something else set it, e.g. a bill due date, a boss's ask).
- "deadline_date": an ISO date (YYYY-MM-DD) if the task text implies one,
  otherwise null. Resolve relative dates ("Tuesday", "tomorrow") against
  today's date above.
- "deadline_passed": true if deadline_date is before today, else false.
- "has_meaningful_consequence": true if skipping this has a real cost
  (money, relationship, job, health), false for low-stakes tasks.
- "time_estimate": one of {TIME_BUCKETS}, your best-guess estimate. Be
  realistic and slightly generous — ADHD users chronically underestimate.
- "urgency_score": integer 0-40, built from: deadline already passed (+15),
  external deadline (+10), meaningful consequence (+10), and proximity of
  the deadline (due today +15, this week +10, next ~2 weeks +5, none/far
  +0). Cap at 40.
- "importance_score": integer 0-30 for how directly the task serves the
  chosen value: directly critical to it = 30, moderately tied = 15,
  loosely/weakly tied = 5.
- "total_score": urgency_score + importance_score.

Return ONLY a JSON array of these objects, one per input task, in the same
order as given. No prose, no markdown fences."""


def _score_and_sort(tagged: list[dict]) -> list[dict]:
    for t in tagged:
        bucket = t.get("time_estimate")
        effort = EFFORT_WEIGHT.get(bucket, 0)
        t["effort_weight"] = effort
        t["display_score"] = t.get("total_score", 0) + effort
        t["needs_calendar"] = bucket in ("30-60min", ">60min")
    return sorted(tagged, key=lambda t: t["display_score"], reverse=True)


@app.post("/api/prioritize")
def prioritize(req: PrioritizeRequest):
    lines = [l.strip() for l in req.tasks.splitlines() if l.strip()]
    if not lines:
        raise HTTPException(400, "No tasks provided.")
    if not req.values:
        raise HTTPException(400, "Pick at least one core value first.")

    values = [v for v in req.values if v]
    user_prompt = (
        "The user's chosen core values, in their own priority order: "
        + ", ".join(values)
        + "\n\nTasks (one per line):\n"
        + "\n".join(f"- {l}" for l in lines)
    )

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )

    raw = "".join(b.text for b in response.content if b.type == "text").strip()
    try:
        tagged = json.loads(raw)
    except json.JSONDecodeError:
        raise HTTPException(502, f"Model returned unparseable output: {raw[:500]}")

    return {"tasks": _score_and_sort(tagged), "effort_weights": EFFORT_WEIGHT}


app.mount("/", StaticFiles(directory="static", html=True), name="static")
