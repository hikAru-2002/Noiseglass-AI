from database import SessionLocal
from models import AnalysisRun, Ticket, ClusterSummary, ActiveTicket

def save_analysis_run(tickets: list[dict], result: dict, source: str | None = None) -> int:
    """Persist a completed analysis run to Postgres. Returns the new run's id."""
    db = SessionLocal()
    try:
        run = AnalysisRun(
            total_tickets_analyzed=result["total_tickets_analyzed"],
            noise_filtered_count=result["noise_filtered_count"],
            source=source,
        )
        db.add(run)
        db.flush()  # assigns run.id before we use it below

        cluster_categories = {c["category"] for c in result["actionable_clusters"]}
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

def list_runs(limit: int = 20) -> list[dict]:
    """Return recent analysis runs, newest first, for the history view."""
    db = SessionLocal()
    try:
        rows = (
            db.query(AnalysisRun)
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


def load_active_tickets() -> list[dict]:
    """Load the current active ticket set from Postgres."""
    db = SessionLocal()
    try:
        rows = db.query(ActiveTicket).all()
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


def get_active_source() -> str | None:
    """Return the source label of the current active ticket set, if any."""
    db = SessionLocal()
    try:
        row = db.query(ActiveTicket).first()
        return row.source if row else None
    finally:
        db.close()


def save_active_tickets(tickets: list[dict], source: str = "synthetic"):
    """Replace the active ticket set in Postgres with a new one."""
    db = SessionLocal()
    try:
        db.query(ActiveTicket).delete()
        for t in tickets:
            db.add(ActiveTicket(
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