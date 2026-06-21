# Signal — Support Trend Intelligence for Flowline

A small tool that turns a pile of noisy support tickets into a ranked list of
actionable product signals — using the real Claude API to classify and
summarize, and plain Python to compute trend math (never trust an LLM to do
arithmetic).

Built as a portfolio project to demonstrate the "surface support ticket
trends to the product team" + "automate repetitive workflows with lightweight
tooling" parts of a CS/support-tooling role.

## How it works

1. **Synthetic dataset** — 80-90 realistic, messy support tickets for a
   fictional B2B workflow-automation SaaS ("Flowline"), spread across a 4-week
   window, with intentional noise: vague one-liners, off-topic tickets,
   duplicates phrased differently by different customers.
2. **Pass 1 — classify** (Claude API): each ticket is read and classified into
   a category + a normalized one-sentence issue description, batched to keep
   API calls efficient.
3. **Pass 2 — cluster + trend math** (plain Python, deterministic): tickets
   are grouped by category, and week-over-week volume change is computed in
   code — not asked of the model, since trend math should never be left to
   an LLM to "remember" or estimate.
4. **Pass 3 — summarize** (Claude API): for clusters with enough volume to
   matter, Claude writes a short, specific headline, a concrete suggested
   action, and a severity rating — given the real computed numbers as ground
   truth, not asked to invent them.
5. **Frontend**: a dashboard showing the raw "incoming" stream resolving into
   ranked "signal" cards, each expandable into trend sparkline + sample
   tickets + suggested action.

## Running it locally

### 1. Backend

```bash
cd backend
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...   # your own key
python3 -m uvicorn main:app --reload --port 8000
```

Optional — run a quick standalone smoke test of the full pipeline first
(prints results to your terminal, writes `test_output.json`):

```bash
python3 test_pipeline.py
```

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open the printed local URL (usually `http://localhost:5173`). The dev server
proxies `/api/*` to the backend on port 8000.

### 3. Use it

- The left panel shows the raw incoming ticket stream.
- Click **Run analysis** — this fires the real Claude API calls (takes
  ~20–40 seconds for ~90 tickets). Results are cached to
  `backend/data/analysis_cache.json` so refreshing the page doesn't re-spend
  API credits.
- Click any signal card to expand it: see the trend sparkline, suggested
  action, and a few real sample tickets that fed into that cluster.
- **Re-run analysis** any time, or hit `POST /api/regenerate-tickets` to get
  a fresh synthetic dataset with a new random seed (different trend shapes).

## Project structure

```
backend/
  main.py                 FastAPI app, 4 endpoints
  engine.py                core classify -> cluster -> summarize pipeline
  test_pipeline.py          standalone smoke test, run before starting the server
  data/seed_tickets.py      synthetic dataset generator
  requirements.txt
frontend/
  src/App.jsx               main layout + state
  src/components/           IncomingStream, SignalCard, EmptyState
  src/App.css               design system (ink/amber/teal palette)
```

## Design notes

The visual metaphor is literal: noisy, unsorted tickets stream in on the
left; running analysis resolves them into a small number of confident,
ranked "signals" on the right, each with a clear severity, trend direction,
and next step — the same mental model a support-ops or product person
actually uses when triaging ticket volume.
