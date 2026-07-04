# Noiseglass — Support Trend Intelligence

**Live at [noiseglass.vercel.app](https://noiseglass.vercel.app)**

Noiseglass is an AI-powered support intelligence platform that transforms noisy customer feedback into ranked, actionable product insights. It uses the Claude API to classify and summarize issues while relying on deterministic Python code for clustering and trend analysis, so every number is accurate and reproducible — the LLM never does the math.

Built as a portfolio project, Noiseglass demonstrates how modern AI can automate support operations: identifying recurring problems, prioritizing emerging trends, and surfacing insights product and engineering teams can act on immediately.

## How it works

1. **Ingestion** — Pull real feedback from multiple sources: GitHub Issues (REST API), App Store reviews (Apple RSS), Reddit posts, Zendesk tickets, uploaded CSVs, or pasted text. A synthetic dataset is included for instant demos.

2. **Pass 1, AI classification** — Claude (Haiku) reads batches of raw tickets in parallel and classifies each into a normalized category with a concise issue summary. Prompts are source-aware, so GitHub issues, app reviews, and support tickets are each interpreted in their proper context.

3. **Pass 2, deterministic analysis** — Python groups classified tickets into clusters and computes week-over-week trends, frequency, and volume. All arithmetic happens in code, not in the language model.

4. **Pass 3, AI summarization** — Claude (Sonnet) receives the computed statistics and writes a product-team-facing headline, suggested action, and severity for each cluster — grounded in the verified numbers.

5. **Visualization** — A live dashboard shows the raw incoming stream beside ranked signals, with severity tiers, trend percentages, drill-down ticket details, keyboard-driven search, and run history.

## Technology

* **Frontend:** React + Vite, deployed on Vercel
* **Backend:** FastAPI, deployed on Railway
* **AI:** Claude API (Haiku for classification, Sonnet for summarization)
* **Database:** PostgreSQL + SQLAlchemy; SQLite fallback for local dev
* **Migrations:** Alembic
* **Integrations:** GitHub REST API, Apple App Store RSS, Reddit, Zendesk

## Running locally

### Backend

```bash
cd backend
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...
python -m uvicorn main:app --reload --port 8000
```

To verify the complete pipeline independently:

```bash
python test_pipeline.py
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open the local URL displayed by Vite. The frontend targets the API at `VITE_API_URL` (defaults to `http://localhost:8000`).

## Features

* AI-powered classification with source-aware prompts
* Live ingestion: GitHub Issues, App Store reviews, Reddit posts, Zendesk tickets, CSV upload, pasted text
* Trend detection using deterministic Python calculations over 4-week windows
* AI-generated headlines, recommended actions, and severity ratings
* Four-tier signal ranking (severe / high / moderate / low) blending severity, momentum, and volume
* PostgreSQL persistence of every run — tickets, clusters, and history survive redeploys
* Cached analysis results to avoid repeated API costs
* Keyboard-first UI: `/` to search, `Esc` to dismiss

## Project structure

```
backend/
  main.py                    FastAPI application and endpoints
  engine.py                  Two-pass Claude analysis pipeline
  database.py                Postgres/SQLite configuration
  models.py                  SQLAlchemy models
  persistence.py             Run history and active ticket storage
  github_ingest.py           GitHub Issues integration
  appstore_ingest.py         App Store reviews integration
  reddit_ingest.py           Reddit posts integration
  zendesk_ingest.py          Zendesk tickets integration
  ingest.py                  CSV and pasted-text parsing
  run_scheduled_analysis.py  Cron entrypoint for scheduled runs
  test_pipeline.py           Pipeline smoke tests
  alembic/                   Database migrations

frontend/
  src/
    Landing.jsx              Marketing page
    Dashboard.jsx            Analysis console
    components/              Stream, signal cards, detail panel, history
```

## Design philosophy

Support teams receive hundreds of repetitive tickets that obscure the problems that matter. Noiseglass reduces that noise by combining AI classification with deterministic analytics: trust the LLM to read messy human text, trust code to count. The result is trend numbers a team can defend and act on.
