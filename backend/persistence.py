from datetime import datetime, timezone

from database import SessionLocal
from models import AnalysisRun, Ticket, ClusterSummary, ActiveTicket, AnalysisCache

DEFAULT_WORKSPACE = "public"


def save_analysis_run(
    tickets: list[dict],
    result: dict,
    source: str | None = None,
    workspace_id: str = DEFAULT_WORKSPACE,
) -> int:
    """Persist a completed analysis run to Postgres. Returns the new run's id."""
    db = SessionLocal()
    try:
        run = AnalysisRun(
            total_tickets_analyzed=result["total_tickets_analyzed"],
            noise_filtered_count=result["noise_filtered_count"],
            source=source,
            workspace_id=workspace_id,
        )
        db.add(run)
        db.flush()  # assigns run.id before we use it below

        ticket_meta = {}
        for cluster in result["actionable_clusters"]:
            for t in cluster.get("sample_tickets", []):
                ticket_meta[t["id"]] = {
                    "category": cluster["category"],
                    "normalized_issue": t.get("normalized_issue"),
                }

        for t in tickets:
            meta = ticket_meta.get(t["id"], {})
            db.add(Ticket(
                id=f"{run.id}-{t['id']}",  # prefix avoids collisions across runs
                run_id=run.id,
                created_at=t["created_at"],
                customer_name=t["customer_name"],
                company=t["company"],
                channel=t["channel"],
                subject=t["subject"],
                body=t["body"],
                category=meta.get("category"),
                normalized_issue=meta.get("normalized_issue"),
                is_actionable_signal=t["id"] in ticket_meta,
            ))

        for c in result["actionable_clusters"]:
            db.add(ClusterSummary(
                run_id=run.id,
                category=c["category"],
                total_tickets=c["total_tickets"],
                week_counts=c["week_counts"],
                trend_pct_vs_last_week=c["trend_pct_vs_last_week"],
                sample_issues=c["sample_issues"],
                headline=c.get("headline"),
                suggested_action=c.get("suggested_action"),
                severity=c.get("severity"),
            ))

        db.commit()
        return run.id
    finally:
        db.close()


def list_runs(limit: int = 20, workspace_id: str = DEFAULT_WORKSPACE) -> list[dict]:
    """Return recent analysis runs for a workspace, newest first."""
    db = SessionLocal()
    try:
        rows = (
            db.query(AnalysisRun)
            .filter(AnalysisRun.workspace_id == workspace_id)
            .order_by(AnalysisRun.generated_at.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "id": r.id,
                "generated_at": r.generated_at.isoformat() if r.generated_at else None,
                "total_tickets_analyzed": r.total_tickets_analyzed,
                "noise_filtered_count": r.noise_filtered_count,
                "cluster_count": len(r.clusters),
                "source": r.source,
            }
            for r in rows
        ]
    finally:
        db.close()


def load_active_tickets(workspace_id: str = DEFAULT_WORKSPACE) -> list[dict]:
    """Load a workspace's current active ticket set."""
    db = SessionLocal()
    try:
        rows = (
            db.query(ActiveTicket)
            .filter(ActiveTicket.workspace_id == workspace_id)
            .all()
        )
        return [
            {
                "id": r.id,
                "created_at": r.created_at,
                "customer_name": r.customer_name,
                "company": r.company,
                "channel": r.channel,
                "subject": r.subject,
                "body": r.body,
            }
            for r in rows
        ]
    finally:
        db.close()


def get_active_source(workspace_id: str = DEFAULT_WORKSPACE) -> str | None:
    """Return the source label of a workspace's active ticket set, if any."""
    db = SessionLocal()
    try:
        row = (
            db.query(ActiveTicket)
            .filter(ActiveTicket.workspace_id == workspace_id)
            .first()
        )
        return row.source if row else None
    finally:
        db.close()


def save_active_tickets(
    tickets: list[dict],
    source: str = "synthetic",
    workspace_id: str = DEFAULT_WORKSPACE,
):
    """Replace one workspace's active ticket set. Other workspaces untouched."""
    db = SessionLocal()
    try:
        db.query(ActiveTicket).filter(
            ActiveTicket.workspace_id == workspace_id
        ).delete()
        for t in tickets:
            db.add(ActiveTicket(
                workspace_id=workspace_id,
                id=t["id"],
                created_at=t["created_at"],
                customer_name=t["customer_name"],
                company=t["company"],
                channel=t["channel"],
                subject=t["subject"],
                body=t["body"],
                source=source,
            ))
        db.commit()
    finally:
        db.close()


def list_active_workspaces() -> list[str]:
    """All workspace ids that currently hold an active ticket set."""
    db = SessionLocal()
    try:
        rows = db.query(ActiveTicket.workspace_id).distinct().all()
        return [r[0] for r in rows]
    finally:
        db.close()


# ------------------------------------------------------------------
# Analysis cache (per workspace, replaces the old on-disk JSON file)
# ------------------------------------------------------------------

def load_cached_analysis(workspace_id: str = DEFAULT_WORKSPACE) -> dict | None:
    db = SessionLocal()
    try:
        row = db.get(AnalysisCache, workspace_id)
        return row.payload if row else None
    finally:
        db.close()


def save_cached_analysis(result: dict, workspace_id: str = DEFAULT_WORKSPACE):
    db = SessionLocal()
    try:
        row = db.get(AnalysisCache, workspace_id)
        if row:
            row.payload = result
            row.generated_at = datetime.now(timezone.utc)
        else:
            db.add(AnalysisCache(workspace_id=workspace_id, payload=result))
        db.commit()
    finally:
        db.close()


def clear_cached_analysis(workspace_id: str = DEFAULT_WORKSPACE):
    db = SessionLocal()
    try:
        row = db.get(AnalysisCache, workspace_id)
        if row:
            db.delete(row)
            db.commit()
    finally:
        db.close()
