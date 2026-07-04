from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from database import Base


class AnalysisRun(Base):
    __tablename__ = "analysis_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    generated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    total_tickets_analyzed = Column(Integer)
    noise_filtered_count = Column(Integer)
    source = Column(String, nullable=True)  # e.g. "github:n8n-io/n8n", "appstore:Clash of Clans"

    tickets = relationship("Ticket", back_populates="run", cascade="all, delete-orphan")
    clusters = relationship("ClusterSummary", back_populates="run", cascade="all, delete-orphan")


class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(String, primary_key=True)  # e.g. "UPL-0001"
    run_id = Column(Integer, ForeignKey("analysis_runs.id"))
    created_at = Column(String)  # stored as ISO string, matches ingest.py output
    customer_name = Column(String)
    company = Column(String)
    channel = Column(String)
    subject = Column(String)
    body = Column(String)

    # Pass 1 classification (nullable until scored)
    category = Column(String, nullable=True)
    normalized_issue = Column(String, nullable=True)
    is_actionable_signal = Column(Boolean, nullable=True)

    run = relationship("AnalysisRun", back_populates="tickets")


class ClusterSummary(Base):
    __tablename__ = "cluster_summaries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(Integer, ForeignKey("analysis_runs.id"))
    category = Column(String)
    total_tickets = Column(Integer)
    week_counts = Column(JSON)  # [this week, last week, 2wk ago, 3wk ago]
    trend_pct_vs_last_week = Column(Float)
    sample_issues = Column(JSON)
    headline = Column(String, nullable=True)
    suggested_action = Column(String, nullable=True)
    severity = Column(String, nullable=True)

    run = relationship("AnalysisRun", back_populates="clusters")

class ActiveTicket(Base):
    """The current working set of tickets shown in the Incoming view.
    Unlike Ticket (which is a snapshot tied to a specific analysis run),
    this table holds whatever ticket set is currently active, whether
    synthetic, uploaded, or pulled from GitHub. Replacing the active set
    deletes all rows and inserts the new ones."""
    __tablename__ = "active_tickets"

    id = Column(String, primary_key=True)
    created_at = Column(String)
    customer_name = Column(String)
    company = Column(String)
    channel = Column(String)
    subject = Column(String)
    body = Column(String)
    source = Column(String, default="synthetic")  # synthetic, github, upload, etc.