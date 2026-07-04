"""
Pulls real GitHub Issues and normalizes them into the same ticket shape
ingest.py produces: { id, created_at, customer_name, company, channel, subject, body }

Uses GitHub's public REST API. If GITHUB_TOKEN is set in the environment,
requests are authenticated for a much higher rate limit (5000/hour instead
of 60/hour unauthenticated).
"""

import os
import requests

GITHUB_API = "https://api.github.com"


def fetch_github_issues(owner: str, repo: str, limit: int = 50) -> list[dict]:
    """Fetch recent issues (not pull requests) from a public GitHub repo,
    normalized into Triage's ticket shape."""
    url = f"{GITHUB_API}/repos/{owner}/{repo}/issues"
    params = {
        "state": "all",
        "per_page": min(limit, 100),
        "sort": "created",
        "direction": "desc",
    }
    headers = {"Accept": "application/vnd.github+json"}

    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    resp = requests.get(url, params=params, headers=headers, timeout=15)
    resp.raise_for_status()
    raw_issues = resp.json()

    tickets = []
    for issue in raw_issues:
        if "pull_request" in issue:
            continue

        body = (issue.get("body") or "").strip()
        if not body:
            continue

        tickets.append({
            "id": f"GH-{issue['number']}",
            "created_at": issue["created_at"],
            "customer_name": issue["user"]["login"],
            "company": f"{owner}/{repo}",
            "channel": "github",
            "subject": issue["title"],
            "body": body[:2000],
        })

    return tickets
