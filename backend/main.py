"""
FastAPI server for Noiseglass, the support ticket trend analyzer.

Every request is scoped to a workspace via the X-Workspace-Id header
(the frontend generates a UUID per browser and sends it on every call).
Requests without the header fall back to the shared "public" workspace,
which keeps old clients and the cron runner working.

Endpoints:
  GET  /api/tickets            -> raw ticket list (for the "incoming" view)
  POST /api/analyze            -> runs the real Claude API analysis, caches result per workspace
  GET  /api/analysis           -> returns cached analysis if present
  POST /api/regenerate-tickets -> regenerates the synthetic dataset with a new seed
  POST /api/upload-csv         -> replace the active ticket set with an uploaded CSV
  POST /api/upload-text        -> replace the active ticket set with pasted free text
  POST /api/fetch-github-issues -> replace the active ticket set with real GitHub issues
  POST /api/fetch-zendesk-tickets, /api/fetch-appstore-reviews, /api/fetch-reddit-posts
  GET  /api/runs               -> analysis run history for this workspace
"""

import os
import re
import sys
import time
import traceback
from collections import defaultdict, deque
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Header
from fastapi.middleware.cors import CORSMiddleware

sys.path.insert(0, str(Path(__file__).parent))

from data.seed_tickets import generate_tickets
from engine import run_full_analysis
from ingest import parse_csv_tickets, parse_pasted_tickets
from persistence import (
    save_analysis_run,
    load_active_tickets,
    save_active_tickets,
    list_runs,
    get_active_source,
    load_cached_analysis,
    save_cached_analysis,
    clear_cached_analysis,
)
from github_ingest import fetch_github_issues
from zendesk_ingest import fetch_zendesk_tickets
from appstore_ingest import fetch_appstore_reviews
from reddit_ingest import fetch_reddit_posts

# Local dev on SQLite has no Alembic history, so create tables directly.
# On Railway (Postgres) the schema is managed by Alembic migrations.
from database import engine, IS_SQLITE, Base
import models  # noqa: F401  (registers models on Base.metadata)

if IS_SQLITE:
    Base.metadata.create_all(bind=engine)


app = FastAPI(title="Noiseglass API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------------------------------------------------
# Workspace scoping
# ------------------------------------------------------------------

_WS_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def _workspace(x_workspace_id: str | None) -> str:
    """Sanitize the workspace header. Anything malformed maps to 'public'
    rather than erroring, so old clients keep working."""
    if x_workspace_id and _WS_PATTERN.match(x_workspace_id):
        return x_workspace_id
    return "public"


# ------------------------------------------------------------------
# Rate limiting (in-memory, per workspace). Protects the Anthropic key
# and the external APIs from abuse. Resets on process restart, which is
# fine for this tier of protection.
# ------------------------------------------------------------------

_rate_buckets: dict[tuple[str, str], deque] = defaultdict(deque)

LIMITS = {
    "analyze": (4, 600),   # 4 runs per 10 minutes per workspace
    "fetch": (20, 600),    # 20 source fetches per 10 minutes per workspace
}


def _check_rate(workspace: str, bucket: str):
    max_calls, window = LIMITS[bucket]
    q = _rate_buckets[(workspace, bucket)]
    now = time.monotonic()
    while q and now - q[0] > window:
        q.popleft()
    if len(q) >= max_calls:
        retry_in = int(window - (now - q[0])) + 1
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit reached. Try again in about {max(retry_in // 60, 1)} minute(s).",
        )
    q.append(now)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _load_tickets(ws: str):
    tickets = load_active_tickets(ws)
    if not tickets:
        tickets = generate_tickets()
        save_active_tickets(tickets, source="synthetic", workspace_id=ws)
    return tickets


def _replace_active_tickets(tickets: list[dict], source: str, ws: str):
    save_active_tickets(tickets, source=source, workspace_id=ws)
    clear_cached_analysis(ws)


def _describe_source(ws: str) -> str | None:
    """Turn the stored source label into a human-readable phrase for the
    AI prompts, so Claude knows what kind of feedback it is reading."""
    source = get_active_source(ws)
    if not source:
        return None
    kind, _, detail = source.partition(":")
    templates = {
        "github": f"GitHub issues from the repository {detail}",
        "appstore": f"public App Store reviews of the app '{detail}'",
        "reddit": f"Reddit posts matching {detail}",
        "zendesk": f"Zendesk support tickets from {detail}",
        "upload": "support tickets uploaded by the user",
        "synthetic": "synthetic demo support tickets for a B2B SaaS workflow automation product called Flowline",
    }
    return templates.get(kind)


# ------------------------------------------------------------------
# Endpoints
# ------------------------------------------------------------------

@app.get("/api/tickets")
def get_tickets(x_workspace_id: str | None = Header(None)):
    ws = _workspace(x_workspace_id)
    tickets = _load_tickets(ws)
    return [{k: v for k, v in t.items() if k != "_true_cluster"} for t in tickets]


@app.get("/api/analysis")
def get_cached_analysis(x_workspace_id: str | None = Header(None)):
    ws = _workspace(x_workspace_id)
    cached = load_cached_analysis(ws)
    if cached is None:
        return {"cached": False}
    return {"cached": True, **cached}


@app.post("/api/analyze")
def analyze(x_workspace_id: str | None = Header(None)):
    ws = _workspace(x_workspace_id)
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise HTTPException(
            status_code=500,
            detail="ANTHROPIC_API_KEY is not set in the environment. Set it before running analysis.",
        )
    _check_rate(ws, "analyze")
    tickets = _load_tickets(ws)
    try:
        result = run_full_analysis(tickets, source_context=_describe_source(ws))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    save_cached_analysis(result, ws)

    try:
        run_id = save_analysis_run(
            tickets, result, source=get_active_source(ws), workspace_id=ws
        )
        result["db_run_id"] = run_id
    except Exception as e:
        print(f"Warning: failed to save analysis run to database: {e}", flush=True)
        traceback.print_exc()
        sys.stdout.flush()

    return {"cached": False, **result}


@app.post("/api/regenerate-tickets")
def regenerate_tickets(seed: int = 0, x_workspace_id: str | None = Header(None)):
    import random

    ws = _workspace(x_workspace_id)
    seed = seed or random.randint(1, 100000)
    tickets = generate_tickets(seed=seed)
    _replace_active_tickets(tickets, "synthetic", ws)
    return {"seed": seed, "count": len(tickets)}


@app.post("/api/upload-csv")
async def upload_csv(file: UploadFile = File(...), x_workspace_id: str | None = Header(None)):
    ws = _workspace(x_workspace_id)
    raw_bytes = await file.read()
    try:
        csv_text = raw_bytes.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="Could not read file as UTF-8 text. Please export as a plain CSV.")

    tickets = parse_csv_tickets(csv_text)
    if not tickets:
        raise HTTPException(
            status_code=400,
            detail="No usable tickets found. Make sure your CSV has a header row with a text column (e.g. 'body', 'description', or 'message').",
        )
    _replace_active_tickets(tickets, "upload", ws)
    return {"count": len(tickets)}


@app.post("/api/upload-text")
def upload_text(text: str = Form(...), x_workspace_id: str | None = Header(None)):
    ws = _workspace(x_workspace_id)
    tickets = parse_pasted_tickets(text)
    if not tickets:
        raise HTTPException(status_code=400, detail="No ticket lines found in the pasted text.")
    _replace_active_tickets(tickets, "upload", ws)
    return {"count": len(tickets)}


@app.post("/api/fetch-github-issues")
def fetch_github_issues_endpoint(
    owner: str = Form(...),
    repo: str = Form(...),
    limit: int = Form(100),
    x_workspace_id: str | None = Header(None),
):
    ws = _workspace(x_workspace_id)
    _check_rate(ws, "fetch")
    try:
        tickets = fetch_github_issues(owner, repo, limit)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch from GitHub: {e}")
    if not tickets:
        raise HTTPException(status_code=400, detail="No usable issues found in that repo.")
    _replace_active_tickets(tickets, f"github:{owner}/{repo}", ws)
    return {"count": len(tickets), "source": f"{owner}/{repo}"}


@app.post("/api/fetch-zendesk-tickets")
def fetch_zendesk_tickets_endpoint(
    subdomain: str = Form(""),
    email: str = Form(""),
    api_token: str = Form(""),
    limit: int = Form(100),
    x_workspace_id: str | None = Header(None),
):
    ws = _workspace(x_workspace_id)
    _check_rate(ws, "fetch")
    # Fall back to env credentials so a deployed instance can be
    # pre-configured without users typing tokens into the UI.
    subdomain = subdomain.strip() or os.environ.get("ZENDESK_SUBDOMAIN", "")
    email = email.strip() or os.environ.get("ZENDESK_EMAIL", "")
    api_token = api_token.strip() or os.environ.get("ZENDESK_API_TOKEN", "")

    if not (subdomain and email and api_token):
        raise HTTPException(
            status_code=400,
            detail="Zendesk subdomain, email, and API token are required (via form or ZENDESK_* env vars).",
        )

    try:
        tickets = fetch_zendesk_tickets(subdomain, email, api_token, limit)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch from Zendesk: {e}")
    if not tickets:
        raise HTTPException(status_code=400, detail="No usable tickets found in that Zendesk instance.")
    _replace_active_tickets(tickets, f"zendesk:{subdomain}.zendesk.com", ws)
    return {"count": len(tickets), "source": f"{subdomain}.zendesk.com"}


@app.post("/api/fetch-appstore-reviews")
def fetch_appstore_reviews_endpoint(
    app_term: str = Form(...),
    country: str = Form("us"),
    limit: int = Form(100),
    x_workspace_id: str | None = Header(None),
):
    ws = _workspace(x_workspace_id)
    _check_rate(ws, "fetch")
    try:
        tickets = fetch_appstore_reviews(app_term, country, limit)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch App Store reviews: {e}")
    if not tickets:
        raise HTTPException(status_code=400, detail="No reviews found for that app.")
    _replace_active_tickets(tickets, f"appstore:{app_term}", ws)
    return {"count": len(tickets), "source": f"App Store: {app_term}"}


@app.post("/api/fetch-reddit-posts")
def fetch_reddit_posts_endpoint(
    query: str = Form(...),
    subreddit: str = Form(""),
    limit: int = Form(100),
    x_workspace_id: str | None = Header(None),
):
    ws = _workspace(x_workspace_id)
    _check_rate(ws, "fetch")
    try:
        tickets = fetch_reddit_posts(query, subreddit, limit)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch from Reddit: {e}")
    if not tickets:
        raise HTTPException(
            status_code=400,
            detail="No text posts found for that search. Try a broader query or a product subreddit.",
        )
    scope = f"r/{subreddit}" if subreddit.strip() else "all of Reddit"
    _replace_active_tickets(tickets, f"reddit:'{query}' in {scope}", ws)
    return {"count": len(tickets), "source": f"Reddit: '{query}' in {scope}"}


@app.get("/api/runs")
def get_runs(limit: int = 20, x_workspace_id: str | None = Header(None)):
    ws = _workspace(x_workspace_id)
    try:
        return {"runs": list_runs(limit, workspace_id=ws)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load run history: {e}")


@app.get("/api/health")
def health():
    return {"status": "ok", "api_key_set": bool(os.environ.get("ANTHROPIC_API_KEY"))}
