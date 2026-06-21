"""FastAPI backend for Signal."""
import json
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from data.seed_tickets import generate_tickets
from engine import run_pipeline

app = FastAPI(title="Signal API")

# CORS for frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory cache
_cache = {"result": None, "tickets": None}


class AnalysisRequest(BaseModel):
    """Request to run analysis."""
    pass


class RegenerateRequest(BaseModel):
    """Request to regenerate tickets."""
    seed: int = None


@app.get("/api/health")
def health():
    """Health check."""
    return {"status": "ok"}


@app.get("/api/tickets")
def get_tickets():
    """Get current ticket stream."""
    if _cache["tickets"] is None:
        _cache["tickets"] = generate_tickets(seed=42)
    return {"tickets": _cache["tickets"]}


@app.post("/api/analyze")
def analyze(req: AnalysisRequest):
    """Run the full analysis pipeline."""
    if _cache["tickets"] is None:
        _cache["tickets"] = generate_tickets(seed=42)
    
    result = run_pipeline(_cache["tickets"])
    _cache["result"] = result
    
    return {
        "signals": result["signals"],
        "trends": result["trends"],
    }


@app.post("/api/regenerate-tickets")
def regenerate_tickets(req: RegenerateRequest):
    """Generate a fresh synthetic dataset."""
    seed = req.seed if req.seed is not None else None
    _cache["tickets"] = generate_tickets(seed=seed)
    _cache["result"] = None  # Clear cached analysis
    
    return {"count": len(_cache["tickets"]), "tickets": _cache["tickets"]}


@app.get("/api/result")
def get_result():
    """Get cached analysis result."""
    if _cache["result"] is None:
        return {"error": "No analysis run yet. POST to /api/analyze first."}
    return _cache["result"]


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

