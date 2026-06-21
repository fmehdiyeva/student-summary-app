# StudySum

A study tool that helps students learn faster. Upload a PDF or paste a YouTube
link and get a clean, structured summary — overview, key concepts, formulas
worth memorizing, and self-test questions. It can also "humanize" AI-generated
text so it reads more naturally.

**Live demo:** https://student-summary-app.onrender.com

> Hosted on Render's free tier — the first load after a period of inactivity
> may take ~30s while the server wakes up.

## Features

- **PDF summaries** — extracts text with `pypdf` and summarizes it.
- **YouTube summaries** — pulls the transcript via `youtube-transcript-api`.
- **Summaries in any language** — pick the output language per request.
- **Text humanizer** — rewrites stiff AI text into natural prose.
- **Rate limiting** — `flask-limiter` caps requests to protect the API quota.

## Tech stack

- **Backend:** Python, Flask, Gunicorn
- **LLM:** OpenRouter API (via the Anthropic SDK)
- **Parsing:** pypdf, youtube-transcript-api

## Running locally

```bash
pip install -r requirements.txt
echo "OPENROUTER_API_KEY=your-key-here" > .env
python app.py
```

Then open http://localhost:5000.

## Deployment

Deployed on [Render](https://render.com) using the included `Procfile`
(`gunicorn app:app`). The `OPENROUTER_API_KEY` is configured as an environment
variable in the hosting dashboard, never committed to the repo.
