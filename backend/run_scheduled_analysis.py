"""
Scheduled analysis runner for Railway cron.

For each workspace that has an active ticket set, runs the full
Claude + deterministic analysis and saves the run. Designed to run as a
Railway cron service (e.g. "0 9 * * *" for daily at 9am UTC) with the
same DATABASE_URL and ANTHROPIC_API_KEY as the API service.

MAX_WORKSPACES caps the per-invocation cost: each workspace analysis
costs real API money, so a runaway number of abandoned workspaces can't
drain the budget. Workspaces are processed in arbitrary order; raise the
cap if legitimate usage outgrows it.

Start command on Railway: python run_scheduled_analysis.py
"""

import os
import sys
from datetime import datetime, timezone

from engine import run_full_analysis
from persistence import (
    load_active_tickets,
    save_analysis_run,
    save_cached_analysis,
    get_active_source,
    list_active_workspaces,
)

MAX_WORKSPACES = int(os.environ.get("CRON_MAX_WORKSPACES", "10"))


def main() -> int:
    started = datetime.now(timezone.utc)
    print(f"[cron] scheduled analysis starting at {started.isoformat()}", flush=True)

    workspaces = list_active_workspaces()
    if not workspaces:
        print("[cron] no active workspaces, nothing to analyze.", flush=True)
        return 0

    if len(workspaces) > MAX_WORKSPACES:
        print(
            f"[cron] {len(workspaces)} workspaces found, capping at {MAX_WORKSPACES}.",
            flush=True,
        )
        workspaces = workspaces[:MAX_WORKSPACES]

    failures = 0
    for ws in workspaces:
        tickets = load_active_tickets(ws)
        if not tickets:
            continue
        print(f"[cron] workspace {ws}: analyzing {len(tickets)} tickets...", flush=True)
        try:
            source = get_active_source(ws)
            result = run_full_analysis(tickets)
            save_cached_analysis(result, ws)
            run_id = save_analysis_run(tickets, result, source=source, workspace_id=ws)
            print(
                f"[cron] workspace {ws}: run {run_id} saved, "
                f"{len(result['actionable_clusters'])} clusters, "
                f"{result['noise_filtered_count']} noise.",
                flush=True,
            )
        except Exception as e:
            failures += 1
            print(f"[cron] workspace {ws} FAILED: {e}", flush=True)

    elapsed = (datetime.now(timezone.utc) - started).total_seconds()
    print(f"[cron] done in {elapsed:.1f}s, {failures} failure(s).", flush=True)
    return 1 if failures and failures == len(workspaces) else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"[cron] FAILED: {e}", flush=True)
        sys.exit(1)
