"""
Pulls real Zendesk tickets and normalizes them into the same ticket shape
ingest.py produces: { id, created_at, customer_name, company, channel, subject, body }

Auth: Zendesk API token auth — basic auth with "{email}/token" as the
username and the API token as the password. Credentials can be passed per
request or set in the environment as ZENDESK_SUBDOMAIN / ZENDESK_EMAIL /
ZENDESK_API_TOKEN.
"""

import requests


def fetch_zendesk_tickets(
    subdomain: str,
    email: str,
    api_token: str,
    limit: int = 100,
) -> list[dict]:
    """Fetch recent tickets from a Zendesk instance, normalized into
    Triage's ticket shape. Sideloads users to resolve requester names."""
    url = f"https://{subdomain}.zendesk.com/api/v2/tickets.json"
    params = {
        "sort_by": "created_at",
        "sort_order": "desc",
        "per_page": min(limit, 100),
        "include": "users",
    }
    auth = (f"{email}/token", api_token)

    resp = requests.get(url, params=params, auth=auth, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    users_by_id = {u["id"]: u for u in data.get("users", [])}

    tickets = []
    for t in data.get("tickets", []):
        body = (t.get("description") or "").strip()
        if not body:
            continue

        requester = users_by_id.get(t.get("requester_id"), {})
        via = (t.get("via") or {}).get("channel", "zendesk")

        tickets.append({
            "id": f"ZD-{t['id']}",
            "created_at": t["created_at"],
            "customer_name": requester.get("name", "unknown"),
            "company": subdomain,
            "channel": f"zendesk/{via}" if via != "zendesk" else "zendesk",
            "subject": (t.get("subject") or body[:60]).strip(),
            "body": body[:2000],
        })

    return tickets
