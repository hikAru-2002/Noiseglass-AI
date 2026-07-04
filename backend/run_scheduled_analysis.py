"""
Scheduled analysis runner for Railway cron.

Loads the current active ticket set from Postgres, runs the full
Claude + deterministic analysis, saves the run, and exits. Designed to
run as a Railway cron service (e.g. "0 9 * * *" for daily at 9am UTC)
with the same DATABASE_URL and ANTHROPIC_API_KEY as the API service.

Start command on Railway: python run_scheduled_analysis.py
"""

import sys
from datetime import datetime, timezone

from engine import run_full_analysis
from persistence import load_active_tickets, save_analysis_run, get_active_source


def main() -> int:
    started = datetime.now(timezone.utc)
    print(f"[cron] scheduled analysis starting at {started.isoformat()}", flush=True)

    tickets = load_active_tickets()
    if not tickets:
        print("[cron] no active tickets in database, nothing to analyze.", flush=True)
        return 0

    print(f"[cron] analyzing {len(tickets)} active tickets...", flush=True)
    result = run_full_analysis(tickets)

    run_id = save_analysis_run(tickets, result, source=get_active_source())
    elapsed = (datetime.now(timezone.utc) - started).total_seconds()
    print(
        f"[cron] run {run_id} saved: {result['total_tickets_analyzed']} tickets, "
        f"{len(result['actionable_clusters'])} clusters, "
        f"{result['noise_filtered_count']} noise, {elapsed:.1f}s",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"[cron] FAILED: {e}", flush=True)
        sys.exit(1)
