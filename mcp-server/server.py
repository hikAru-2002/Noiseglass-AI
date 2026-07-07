"""
Noiseglass MCP server.

Exposes the deployed Noiseglass API as MCP tools, so any MCP-capable AI
assistant (Claude Desktop, Claude Code, etc.) can load raw text, run the
analysis pipeline, and read ranked signals as part of a conversation. This
is deliberately the most universal entry point into Noiseglass: an AI
agent doesn't need a GitHub repo or a Zendesk account, it can hand over
any pile of text (notes, logs, transcripts, tickets, whatever) and get
back ranked, actionable signal.

Design notes:
  - This is a thin client of the hosted REST API. No analysis logic is
    duplicated here; the backend remains the single source of truth.
  - A workspace ID is minted once and persisted to ~/.noiseglass/workspace,
    so MCP usage is isolated from other users exactly like a browser
    session is (same X-Workspace-Id mechanism).
  - Set NOISEGLASS_API_URL to point at a deployed backend; defaults to
    a local dev server.

Run:  python server.py    (stdio transport, for MCP client configs)
"""

import os
import uuid
from pathlib import Path

import requests
from mcp.server.fastmcp import FastMCP

API_URL = os.environ.get("NOISEGLASS_API_URL", "http://localhost:8000").rstrip("/")

mcp = FastMCP("noiseglass")


def _workspace_id() -> str:
    """Stable per-machine workspace, minted on first use."""
    path = Path.home() / ".noiseglass" / "workspace"
    if path.exists():
        ws = path.read_text().strip()
        if ws:
            return ws
    path.parent.mkdir(parents=True, exist_ok=True)
    ws = uuid.uuid4().hex
    path.write_text(ws)
    return ws


def _call(method: str, endpoint: str, **kwargs) -> dict:
    headers = kwargs.pop("headers", {})
    headers["X-Workspace-Id"] = _workspace_id()
    resp = requests.request(
        method, f"{API_URL}{endpoint}", headers=headers, timeout=180, **kwargs
    )
    if not resp.ok:
        try:
            detail = resp.json().get("detail", resp.text[:300])
        except Exception:
            detail = resp.text[:300]
        raise RuntimeError(f"Noiseglass API error ({resp.status_code}): {detail}")
    return resp.json()


def _format_signals(result: dict) -> str:
    clusters = result.get("actionable_clusters", [])
    if not clusters:
        return "Analysis complete, but no actionable signals were found."
    clusters = sorted(clusters, key=lambda c: c.get("total_fragments", 0), reverse=True)
    lines = [
        f"Analyzed {result.get('total_fragments_analyzed', '?')} fragments, "
        f"{result.get('noise_filtered_count', '?')} filtered as noise, "
        f"{len(clusters)} actionable signals:\n"
    ]
    for c in clusters:
        wk = c.get("week_counts", [0, 0, 0, 0])
        lines.append(
            f"- [{c.get('severity', '?').upper()}] {c.get('category', '?')} "
            f"({c.get('total_fragments', 0)} fragments, this wk {wk[0]} vs last wk {wk[1]})\n"
            f"  Headline: {c.get('headline', 'n/a')}\n"
            f"  Suggested action: {c.get('suggested_action', 'n/a')}"
        )
    return "\n".join(lines)


@mcp.tool()
def load_github_issues(owner: str, repo: str, limit: int = 100) -> str:
    """Load open issues from a public GitHub repository into the Noiseglass
    workspace as the active fragment set. Replaces previously loaded data.
    Follow with run_analysis to get ranked signals."""
    data = _call("POST", "/api/fetch-github-issues",
                 data={"owner": owner, "repo": repo, "limit": str(limit)})
    return f"Loaded {data['count']} issues from {data['source']}. Call run_analysis next."


@mcp.tool()
def load_raw_text(text: str) -> str:
    """Load any raw text into the Noiseglass workspace, one fragment per
    line. This is the universal entry point: feedback, interview notes,
    meeting notes, logs, transcripts, or anything else worth mining for
    patterns, from any source, human or AI-collected. Replaces previously
    loaded data."""
    data = _call("POST", "/api/upload-text", data={"text": text})
    return f"Loaded {data['count']} fragments from raw text. Call run_analysis next."


@mcp.tool()
def run_analysis() -> str:
    """Run the full Noiseglass analysis on the currently loaded fragments:
    AI classification (Claude), deterministic Python trend math, and AI
    summaries. Returns ranked signals with severity, week-over-week
    movement, headlines, and suggested actions. May take up to a minute.
    Rate limited to 4 runs per 10 minutes per workspace."""
    result = _call("POST", "/api/analyze")
    return _format_signals(result)


@mcp.tool()
def get_signals() -> str:
    """Return the most recent cached analysis for this workspace without
    spending an API call. Use before run_analysis to check for existing
    results."""
    result = _call("GET", "/api/analysis")
    if not result.get("cached"):
        return "No cached analysis. Load data and call run_analysis."
    return _format_signals(result)


@mcp.tool()
def get_run_history(limit: int = 10) -> str:
    """List this workspace's recent analysis runs: when they ran, what
    source was analyzed, fragment and signal counts."""
    data = _call("GET", f"/api/runs?limit={limit}")
    runs = data.get("runs", [])
    if not runs:
        return "No analysis runs recorded for this workspace yet."
    lines = ["Recent analysis runs (newest first):"]
    for r in runs:
        lines.append(
            f"- {r.get('generated_at', '?')[:16]} | {r.get('source') or 'unknown source'} | "
            f"{r.get('total_fragments_analyzed', '?')} fragments -> {r.get('cluster_count', '?')} signals"
        )
    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run()
