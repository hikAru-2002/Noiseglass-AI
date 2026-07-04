"""
Pulls real Reddit posts mentioning a product and normalizes them into the
same ticket shape ingest.py produces:
  { id, created_at, customer_name, company, channel, subject, body }

Uses Reddit's public JSON API. No auth needed, just a descriptive
User-Agent. Optionally scoped to a single subreddit (e.g. the product's
own community, where the richest feedback lives).
"""

from datetime import datetime, timezone

import requests

HEADERS = {"User-Agent": "triage-signal/1.0 (support trend analyzer)"}


def fetch_reddit_posts(
    query: str,
    subreddit: str = "",
    limit: int = 100,
) -> list[dict]:
    """Fetch recent Reddit posts matching a query, normalized into
    Triage's ticket shape. Only text posts are kept, since link posts
    carry no feedback to analyze."""
    subreddit = subreddit.strip().lstrip("r/").strip("/")
    if subreddit:
        url = f"https://www.reddit.com/r/{subreddit}/search.json"
        params = {
            "q": query,
            "restrict_sr": "1",
            "sort": "new",
            "t": "month",
            "limit": min(limit, 100),
        }
    else:
        url = "https://www.reddit.com/search.json"
        params = {
            "q": query,
            "sort": "new",
            "t": "month",
            "limit": min(limit, 100),
        }

    resp = requests.get(url, params=params, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    children = resp.json().get("data", {}).get("children", [])

    tickets = []
    for child in children:
        post = child.get("data", {})
        body = (post.get("selftext") or "").strip()
        if not body or body in ("[removed]", "[deleted]"):
            continue

        created = datetime.fromtimestamp(
            post.get("created_utc", 0), tz=timezone.utc
        ).isoformat()

        tickets.append({
            "id": f"RD-{post.get('id', str(len(tickets)))}",
            "created_at": created,
            "customer_name": f"u/{post.get('author', 'unknown')}",
            "company": f"r/{post.get('subreddit', 'reddit')}",
            "channel": "reddit",
            "subject": (post.get("title") or body[:60]).strip(),
            "body": body[:2000],
        })

    return tickets
