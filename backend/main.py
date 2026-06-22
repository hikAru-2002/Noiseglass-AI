"""
FastAPI server for Triage — the support ticket trend analyzer.

Endpoints:
  GET  /api/tickets            -> raw ticket list (for the "incoming" view)
  POST /api/analyze            -> runs the real Claude API analysis, caches result to disk
  GET  /api/analysis           -> returns cached analysis if present
  POST /api/regenerate-tickets -> regenerates the synthetic dataset with a new seed
  POST /api/upload-csv         -> replace the active ticket set with an uploaded CSV
  POST /api/upload-text        -> replace the active ticket set with pasted free text
"""

import csv
import io
import json
import os
import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware

sys.path.insert(0, str(Path(__file__).parent))

from data.seed_tickets import generate_tickets
from engine import run_full_analysis
from ingest import parse_csv_tickets, parse_pasted_tickets

app = FastAPI(title="Triage API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_DIR = Path(__file__).parent / "data"
TICKETS_PATH = DATA_DIR / "tickets.json"
ANALYSIS_CACHE_PATH = DATA_DIR / "analysis_cache.json"


def _load_tickets():
    if not TICKETS_PATH.exists():
        tickets = generate_tickets()
        TICKETS_PATH.write_text(json.dumps(tickets, indent=2))
        return tickets
    return json.loads(TICKETS_PATH.read_text())


def _replace_active_tickets(tickets: list[dict]):
    """Swap in a new ticket set as the active dataset, and invalidate any
    cached analysis since it no longer corresponds to this data."""
    TICKETS_PATH.write_text(json.dumps(tickets, indent=2))
    if ANALYSIS_CACHE_PATH.exists():
        ANALYSIS_CACHE_PATH.unlink()


@app.get("/api/tickets")
def get_tickets():
    tickets = _load_tickets()
    # strip the ground-truth field before sending to the frontend —
    # that field exists only so WE can sanity-check the model's clustering
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
        result = run_full_analysis(tickets)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    ANALYSIS_CACHE_PATH.write_text(json.dumps(result, indent=2))
    return {"cached": False, **result}


@app.post("/api/regenerate-tickets")
def regenerate_tickets(seed: int = 0):
    import random

    seed = seed or random.randint(1, 100000)
    tickets = generate_tickets(seed=seed)
    _replace_active_tickets(tickets)
    return {"seed": seed, "count": len(tickets)}


@app.post("/api/upload-csv")
async def upload_csv(file: UploadFile = File(...)):
    raw_bytes = await file.read()
    try:
        csv_text = raw_bytes.decode("utf-8-sig")  # handles Excel's BOM-prefixed CSVs
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="Could not read file as UTF-8 text. Please export as a plain CSV.")

    tickets = parse_csv_tickets(csv_text)
    if not tickets:
        raise HTTPException(
            status_code=400,
            detail="No usable tickets found. Make sure your CSV has a header row with a text column (e.g. 'body', 'description', or 'message').",
        )
    _replace_active_tickets(tickets)
    return {"count": len(tickets)}


@app.post("/api/upload-text")
def upload_text(text: str = Form(...)):
    tickets = parse_pasted_tickets(text)
    if not tickets:
        raise HTTPException(status_code=400, detail="No ticket lines found in the pasted text.")
    _replace_active_tickets(tickets)
    return {"count": len(tickets)}


@app.get("/api/health")
def health():
    return {"status": "ok", "api_key_set": bool(os.environ.get("ANTHROPIC_API_KEY"))}
