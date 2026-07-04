"""
Core analysis engine. Two-pass approach using the real Anthropic API:

Pass 1 (per-ticket, batched): classify each ticket into a short category
label + 1-sentence normalized issue description. This turns noisy raw text
into structured data.

Pass 2 (aggregate): take all the structured pass-1 output, group by category,
compute week-over-week volume trend ourselves (in Python, not the LLM; trend
math should be deterministic, not hallucinated), then ask Claude to write a
short, product-team-facing "signal" summary + suggested action for each
cluster that has enough volume to matter.

This mirrors how you'd actually want this to work in production: don't trust
an LLM to count things or do math, but do trust it to read messy text and
write a clear human summary.
"""

import json
import os
import re
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from functools import partial
from typing import Optional

import anthropic

# Right model for the job: Haiku is fast + cheap and plenty for structured
# classification; Sonnet writes the human-facing brief where quality shows.
MODEL_CLASSIFY = "claude-haiku-4-5"
MODEL_SUMMARIZE = "claude-sonnet-4-6"

client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env


DEFAULT_SOURCE_CONTEXT = "customer feedback for a software product"


def _classify_system_prompt(source_context: str) -> str:
    return f"""You are a support-ops analyst. You will be given a batch of raw feedback items ({source_context}) as a JSON array. Treat each item as a support ticket describing a potential product issue.

For EACH ticket, return a structured classification. Respond with ONLY a JSON array (no markdown fences, no preamble), one object per input ticket, in the same order, with this shape:

{{
  "id": "<ticket id, copied exactly>",
  "category": "<short snake_case category slug you choose, 2-4 words, e.g. csv_export_bug, integration_auth_error, onboarding_confusion, ui_performance, billing_issue, notification_settings, feature_request, off_topic_or_vague>",
  "normalized_issue": "<one neutral sentence describing the underlying issue, stripped of customer-specific phrasing/emotion>",
  "is_actionable_signal": <true/false. false for vague, off-topic, or pure praise tickets that don't represent a real product issue>
}}

Use consistent category slugs across tickets that describe the same underlying problem, even if the customers phrased it very differently. Be specific enough to be useful to a product team, but not so specific that near-duplicate issues get split into different categories. Never use em dashes in any text you write; use commas, periods, or colons instead."""


def _summarize_system_prompt(source_context: str) -> str:
    return f"""You are a support-ops analyst preparing a weekly trends brief for the product team. The underlying data is {source_context}. You will be given a list of issue clusters, each with: category name, ticket count, week-over-week volume numbers (already computed, trust these numbers exactly, do not recompute or contradict them), and a sample of normalized issue descriptions from that cluster.

For each cluster, write:
{{
  "category": "<copied exactly>",
  "headline": "<one short, specific sentence a PM could scan in 3 seconds, citing the actual numbers given>",
  "suggested_action": "<one concrete, specific suggested next step, not generic advice like 'investigate further'>",
  "severity": "<low|medium|high based on volume + trend + how blocking the issue sounds>"
}}

Respond with ONLY a JSON array, no markdown fences, no preamble. Be concrete and specific: reference actual numbers and actual issue content, never generic boilerplate like 'users are experiencing issues.' Never use em dashes in any text you write; use commas, periods, or colons instead."""


def _strip_json_fences(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _classify_batch(batch: list[dict], source_context: str = DEFAULT_SOURCE_CONTEXT) -> list[dict]:
    payload = [
        {"id": t["id"], "subject": t["subject"], "body": t["body"][:600]}
        for t in batch
    ]
    resp = client.messages.create(
        model=MODEL_CLASSIFY,
        max_tokens=4000,
        system=_classify_system_prompt(source_context),
        messages=[{"role": "user", "content": json.dumps(payload)}],
    )
    raw = "".join(block.text for block in resp.content if block.type == "text")
    try:
        return json.loads(_strip_json_fences(raw))
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Failed to parse classification response: {raw[:500]}") from e


def classify_tickets(
    tickets: list[dict],
    batch_size: int = 20,
    source_context: str = DEFAULT_SOURCE_CONTEXT,
) -> list[dict]:
    """Pass 1: classify tickets in parallel batches via the Claude API."""
    batches = [tickets[i : i + batch_size] for i in range(0, len(tickets), batch_size)]
    results = []
    classify = partial(_classify_batch, source_context=source_context)
    with ThreadPoolExecutor(max_workers=min(len(batches), 6)) as pool:
        for parsed in pool.map(classify, batches):
            results.extend(parsed)
    return results


def _week_bucket(created_at: str, now: Optional[datetime] = None) -> int:
    """Returns 0 for this week, 1 for last week, etc."""
    s = created_at
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    ts = datetime.fromisoformat(s)
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=now.tzinfo if now and now.tzinfo else None)
    now = now or datetime.now(ts.tzinfo)
    days_ago = (now - ts).days
    return min(max(days_ago, 0) // 7, 3)  # cap at week 3 (oldest bucket in our 4-week window)


def build_clusters(tickets: list[dict], classifications: list[dict]) -> list[dict]:
    """Join raw tickets with their classifications and group into clusters
    with deterministic, Python-computed trend math."""
    class_by_id = {c["id"]: c for c in classifications}
    ticket_by_id = {t["id"]: t for t in tickets}

    clusters = defaultdict(lambda: {"tickets": [], "week_counts": [0, 0, 0, 0]})

    for tid, cls in class_by_id.items():
        ticket = ticket_by_id.get(tid)
        if not ticket or not cls.get("is_actionable_signal", True):
            continue
        cat = cls["category"]
        week = _week_bucket(ticket["created_at"])
        clusters[cat]["tickets"].append(
            {**ticket, "normalized_issue": cls["normalized_issue"]}
        )
        clusters[cat]["week_counts"][week] += 1

    cluster_list = []
    for cat, data in clusters.items():
        total = len(data["tickets"])
        this_week, last_week = data["week_counts"][0], data["week_counts"][1]
        if last_week == 0:
            trend_pct = 100.0 if this_week > 0 else 0.0
        else:
            trend_pct = round(((this_week - last_week) / last_week) * 100, 1)
        cluster_list.append(
            {
                "category": cat,
                "total_tickets": total,
                "week_counts": data["week_counts"],  # [this week, last week, 2wk ago, 3wk ago]
                "trend_pct_vs_last_week": trend_pct,
                "sample_issues": [t["normalized_issue"] for t in data["tickets"][:6]],
                "sample_tickets": data["tickets"][:4],  # for UI drill-down
            }
        )

    cluster_list.sort(key=lambda c: c["total_tickets"], reverse=True)
    return cluster_list


def summarize_clusters(
    clusters: list[dict],
    min_volume: int = 1,
    source_context: str = DEFAULT_SOURCE_CONTEXT,
) -> list[dict]:
    """Pass 2: ask Claude to write the human-facing brief for clusters with
    enough volume to be worth a product team's attention."""
    relevant = [c for c in clusters if c["total_tickets"] >= min_volume]
    if not relevant:
        return []

    payload = [
        {
            "category": c["category"],
            "total_tickets": c["total_tickets"],
            "week_counts_recent_to_oldest": c["week_counts"],
            "trend_pct_vs_last_week": c["trend_pct_vs_last_week"],
            "sample_issues": c["sample_issues"],
        }
        for c in relevant
    ]

    resp = client.messages.create(
        model=MODEL_SUMMARIZE,
        max_tokens=4000,
        system=_summarize_system_prompt(source_context),
        messages=[{"role": "user", "content": json.dumps(payload)}],
    )
    raw = "".join(block.text for block in resp.content if block.type == "text")
    try:
        summaries = json.loads(_strip_json_fences(raw))
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Failed to parse summary response: {raw[:500]}") from e

    summary_by_cat = {s["category"]: s for s in summaries}
    merged = []
    for c in relevant:
        s = summary_by_cat.get(c["category"], {})
        merged.append({**c, **s})
    return merged


def run_full_analysis(tickets: list[dict], source_context: str | None = None) -> dict:
    source_context = source_context or DEFAULT_SOURCE_CONTEXT
    classifications = classify_tickets(tickets, source_context=source_context)
    clusters = build_clusters(tickets, classifications)
    briefed = summarize_clusters(clusters, source_context=source_context)
    noise_count = len(tickets) - sum(c["total_tickets"] for c in clusters)
    return {
        "generated_at": datetime.now().isoformat(),
        "total_tickets_analyzed": len(tickets),
        "actionable_clusters": briefed,
        "noise_filtered_count": noise_count,
    }
