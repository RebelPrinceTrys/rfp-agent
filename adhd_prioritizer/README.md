# ADHD Prioritizer (v1 — minimal slice)

Paste a raw to-do list, pick your core values once, and get the list back
sorted by what actually needs to happen — each task with a "why," a
consequence if it's skipped, a time estimate you can adjust, and a
one-click "Add to calendar" download for anything over 30 minutes.

## How it works

1. You type/paste your to-dos and pick your core values (money, reputation,
   relationship, ease, fun, family, loyalty, health and wellness).
2. The backend sends the list to Claude with a scoring rubric (see
   `SYSTEM_PROMPT` in `app.py`) and gets back, per task: the value it serves,
   a why, a consequence, a deadline read, a time estimate, and urgency +
   importance scores.
3. The app sorts by `urgency_score + importance_score + effort_weight`
   (effort_weight gives a small boost to quick tasks so easy wins can
   surface — see `EFFORT_WEIGHT` in `app.py`).
4. If you change a task's time estimate in the UI, the score and sort order
   update instantly (no extra API call — the effort weights are a fixed
   table on both ends).
5. Tasks estimated over 30 minutes get an "Add to calendar" button that
   downloads a `.ics` file you can import into Google/Apple/Outlook
   calendar.

## Not in this version (see the deferred "full vision" scope)

- No live calendar write access (Google/Outlook OAuth) — v1 uses downloadable
  `.ics` files instead.
- No custom per-task-type time-estimate helpers ("how many emails are in
  your inbox?"). The model gives one realistic estimate per task.
- No accounts/persistence — nothing is saved between sessions yet.

## Running it locally

```bash
cd adhd_prioritizer
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

export ANTHROPIC_API_KEY=sk-ant-...   # your own key, from console.anthropic.com

uvicorn app:app --reload
```

Then open http://127.0.0.1:8000 in your browser.

## A note on privacy

Your to-do list is sent to the Anthropic API to be scored — it can include
sensitive stuff (health, finances, family). Nothing is stored by this app
itself (no database yet), but don't paste anything you wouldn't want to
leave your machine at all.
