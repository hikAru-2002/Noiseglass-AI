"""
FastAPI server for Signal — the support ticket trend analyzer.

Endpoints:
  GET  /api/tickets          -> raw ticket list (for the "incoming" view)
  POST /api/analyze          -> runs the real Claude API analysis, caches result to disk
  GET  /api/analysis         -> returns cached analysis if present
  POST /api/regenerate-tickets -> regenerates the synthetic dataset with a new seed
"""

import json
import os
import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

sys.path.insert(0, str(Path(__file__).parent))

from data.seed_tickets import generate_tickets
from engine import run_full_analysis

app = FastAPI(title="Signal API")

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
    TICKETS_PATH.write_text(json.dumps(tickets, indent=2))
    if ANALYSIS_CACHE_PATH.exists():
        ANALYSIS_CACHE_PATH.unlink()
    return {"seed": seed, "count": len(tickets)}


@app.get("/api/health")
def health():
    return {"status": "ok", "api_key_set": bool(os.environ.get("ANTHROPIC_API_KEY"))}
