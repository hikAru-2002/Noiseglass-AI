"""
DEPRECATED / UNUSED: Reddit was dropped as a source in the Noiseglass
concept change (fewer, more universal ingestion paths: GitHub, Zendesk,
upload, or any MCP-capable agent via raw text). Nothing imports this
module anymore. Safe to delete this file
(backend/reddit_ingest.py) whenever convenient.

Pulls real Reddit posts mentioning a product and normalizes them into the
same fragment shape ingest.py produces:
  { id, created_at, customer_name, company, channel, subject, body }

Two access paths:
  1. OAuth (preferred): if REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET are set,
     authenticate with Reddit's free application-only OAuth flow. This works
     from cloud/datacenter IPs (Railway, etc.), which Reddit otherwise blocks.
  2. Public JSON fallback: works from residential IPs (local dev), but
     cloud providers usually get 403 "Blocked".

To set up OAuth (free, 2 minutes):
  - Visit https://www.reddit.com/prefs/apps and create an app of type "script"
  - Set REDDIT_CLIENT_ID (under the app name) and REDDIT_CLIENT_SECRET in env
"""

import os
from datetime import datetime, timezone

import requests

USER_AGENT = "noiseglass/1.0 (support trend analyzer; contact via github)"
HEADERS = {"User-Agent": USER_AGENT}

_token_cache = {"token": None, "expires_at": 0.0}


def _get_oauth_token() -> str | None:
    """Application-only OAuth token, cached until shortly before expiry.
    Returns None when credentials are not configured."""
    client_id = os.environ.get("REDDIT_CLIENT_ID", "").strip()
    client_secret = os.environ.get("REDDIT_CLIENT_SECRET", "").strip()
    if not (client_id and client_secret):
        return None

    now = datetime.now(timezone.utc).timestamp()
    if _token_cache["token"] and now < _token_cache["expires_at"]:
        return _token_cache["token"]

    resp = requests.post(
        "https://www.reddit.com/api/v1/access_token",
        auth=(client_id, client_secret),
        data={"grant_type": "client_credentials"},
        headers=HEADERS,
        timeout=15,
    )
    resp.raise_for_status()
    payload = resp.json()
    _token_cache["token"] = payload["access_token"]
    # refresh 60s early to avoid using a token that expires mid-request
    _token_cache["expires_at"] = now + payload.get("expires_in", 3600) - 60
    return _token_cache["token"]


def fetch_reddit_posts(
    query: str,
    subreddit: str = "",
    limit: int = 100,
) -> list[dict]:
    """Fetch recent Reddit posts matching a query, normalized into
    Noiseglass's ticket shape. Only text posts are kept, since link posts
    carry no feedback to analyze."""
    subreddit = subreddit.strip().lstrip("r/").strip("/")

    params = {
        "q": query,
        "sort": "new",
        "t": "month",
        "limit": min(limit, 100),
    }
    if subreddit:
        params["restrict_sr"] = "1"

    token = _get_oauth_token()
    if token:
        base = "https://oauth.reddit.com"
        headers = {**HEADERS, "Authorization": f"Bearer {token}"}
    else:
        base = "https://www.reddit.com"
        headers = HEADERS

    path = f"/r/{subreddit}/search.json" if subreddit else "/search.json"

    try:
        resp = requests.get(base + path, params=params, headers=headers, timeout=15)
        resp.raise_for_status()
    except requests.HTTPError as e:
        if e.response is not None and e.response.status_code == 403 and not token:
            raise RuntimeError(
                "Reddit blocked this server's IP (it blocks most cloud hosts). "
                "Fix: create a free Reddit app at reddit.com/prefs/apps and set "
                "REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET in the environment."
            ) from e
        raise

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
