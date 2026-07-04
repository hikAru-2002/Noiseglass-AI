"""
FastAPI server for Noiseglass, the support ticket trend analyzer.

Endpoints:
  GET  /api/tickets            -> raw ticket list (for the "incoming" view)
  POST /api/analyze            -> runs the real Claude API analysis, caches result to disk
  GET  /api/analysis           -> returns cached analysis if present
  POST /api/regenerate-tickets -> regenerates the synthetic dataset with a new seed
  POST /api/upload-csv         -> replace the active ticket set with an uploaded CSV
  POST /api/upload-text        -> replace the active ticket set with pasted free text
  POST /api/fetch-github-issues -> replace the active ticket set with real GitHub issues
"""

import csv
import io
import json
import os
import sys
import traceback
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
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

DATA_DIR = Path(__file__).parent / "data"
ANALYSIS_CACHE_PATH = DATA_DIR / "analysis_cache.json"


def _load_tickets():
    tickets = load_active_tickets()
    if not tickets:
        tickets = generate_tickets()
        save_active_tickets(tickets, source="synthetic")
    return tickets


def _replace_active_tickets(tickets: list[dict], source: str = "unknown"):
    save_active_tickets(tickets, source=source)
    if ANALYSIS_CACHE_PATH.exists():
        ANALYSIS_CACHE_PATH.unlink()


def _describe_source() -> str | None:
    """Turn the stored source label into a human-readable phrase for the
    AI prompts, so Claude knows what kind of feedback it is reading."""
    source = get_active_source()
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


@app.get("/api/tickets")
def get_tickets():
    tickets = _load_tickets()
    return [{k: v for k, v in t.items() if k != "_true_cluster"} for t in tickets]


@app.get("/api/analysis")
def get_cached_analysis():
    if not ANALYSIS_CACHE_PATH.exists():
        return {"cached": False}
    return {"cached": True, **json.loads(ANALYSIS_CACHE_PATH.read_text())}


@app.post("/api/analyze")
def analyze():
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise HTTPException(
            status_code=500,
            detail="ANTHROPIC_API_KEY is not set in the environment. Set it before running analysis.",
        )
    tickets = _load_tickets()
    try:
        result = run_full_analysis(tickets, source_context=_describe_source())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    ANALYSIS_CACHE_PATH.write_text(json.dumps(result, indent=2))

    try:
        run_id = save_analysis_run(tickets, result)
        result["db_run_id"] = run_id
    except Exception as e:
        print(f"Warning: failed to save analysis run to database: {e}", flush=True)
        traceback.print_exc()
        sys.stdout.flush()

    return {"cached": False, **result}


@app.post("/api/regenerate-tickets")
def regenerate_tickets(seed: int = 0):
    import random

    seed = seed or random.randint(1, 100000)
    tickets = generate_tickets(seed=seed)
    _replace_active_tickets(tickets, source="synthetic")
    return {"seed": seed, "count": len(tickets)}


@app.post("/api/upload-csv")
async def upload_csv(file: UploadFile = File(...)):
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
    _replace_active_tickets(tickets, source="upload")
    return {"count": len(tickets)}


@app.post("/api/upload-text")
def upload_text(text: str = Form(...)):
    tickets = parse_pasted_tickets(text)
    if not tickets:
        raise HTTPException(status_code=400, detail="No ticket lines found in the pasted text.")
    _replace_active_tickets(tickets, source="upload")
    return {"count": len(tickets)}


@app.post("/api/fetch-github-issues")
def fetch_github_issues_endpoint(owner: str = Form(...), repo: str = Form(...), limit: int = Form(100)):
    try:
        tickets = fetch_github_issues(owner, repo, limit)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch from GitHub: {e}")
    if not tickets:
        raise HTTPException(status_code=400, detail="No usable issues found in that repo.")
    _replace_active_tickets(tickets, source=f"github:{owner}/{repo}")
    return {"count": len(tickets), "source": f"{owner}/{repo}"}


@app.post("/api/fetch-zendesk-tickets")
def fetch_zendesk_tickets_endpoint(
    subdomain: str = Form(""),
    email: str = Form(""),
    api_token: str = Form(""),
    limit: int = Form(100),
):
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
    _replace_active_tickets(tickets, source=f"zendesk:{subdomain}.zendesk.com")
    return {"count": len(tickets), "source": f"{subdomain}.zendesk.com"}


@app.post("/api/fetch-appstore-reviews")
def fetch_appstore_reviews_endpoint(
    app_term: str = Form(...),
    country: str = Form("us"),
    limit: int = Form(100),
):
    try:
        tickets = fetch_appstore_reviews(app_term, country, limit)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch App Store reviews: {e}")
    if not tickets:
        raise HTTPException(status_code=400, detail="No reviews found for that app.")
    _replace_active_tickets(tickets, source=f"appstore:{app_term}")
    return {"count": len(tickets), "source": f"App Store: {app_term}"}


@app.post("/api/fetch-reddit-posts")
def fetch_reddit_posts_endpoint(
    query: str = Form(...),
    subreddit: str = Form(""),
    limit: int = Form(100),
):
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
    _replace_active_tickets(tickets, source=f"reddit:'{query}' in {scope}")
    return {"count": len(tickets), "source": f"Reddit: '{query}' in {scope}"}


@app.get("/api/runs")
def get_runs(limit: int = 20):
    try:
        return {"runs": list_runs(limit)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load run history: {e}")


@app.get("/api/health")
def health():
    return {"status": "ok", "api_key_set": bool(os.environ.get("ANTHROPIC_API_KEY"))}