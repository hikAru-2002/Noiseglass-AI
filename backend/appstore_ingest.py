"""
Pulls real Apple App Store customer reviews and normalizes them into the
same ticket shape ingest.py produces:
  { id, created_at, customer_name, company, channel, subject, body }

Uses Apple's public iTunes RSS feed: completely free, no auth, no rate
limit worth worrying about. Works for any iOS app by name or numeric ID.
"""

import requests

SEARCH_API = "https://itunes.apple.com/search"
REVIEWS_RSS = "https://itunes.apple.com/{country}/rss/customerreviews/page={page}/id={app_id}/sortby=mostrecent/json"

HEADERS = {"User-Agent": "triage-signal/1.0"}


def resolve_app(term: str, country: str = "us") -> tuple[int, str]:
    """Resolve an app name (or numeric ID) to (app_id, app_name)."""
    term = term.strip()
    if term.isdigit():
        return int(term), term

    resp = requests.get(
        SEARCH_API,
        params={"term": term, "entity": "software", "limit": 1, "country": country},
        headers=HEADERS,
        timeout=15,
    )
    resp.raise_for_status()
    results = resp.json().get("results", [])
    if not results:
        raise ValueError(f"No iOS app found matching '{term}'.")
    return results[0]["trackId"], results[0]["trackName"]


def fetch_appstore_reviews(term: str, country: str = "us", limit: int = 100) -> list[dict]:
    """Fetch recent App Store reviews for an app, normalized into
    Triage's ticket shape. Ratings are prefixed into the body so the
    analysis engine can weigh sentiment."""
    app_id, app_name = resolve_app(term, country)

    tickets = []
    page = 1
    while len(tickets) < limit and page <= 5:
        url = REVIEWS_RSS.format(country=country, page=page, app_id=app_id)
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        feed = resp.json().get("feed", {})
        entries = feed.get("entry", [])
        # first entry on page 1 is app metadata, not a review
        if isinstance(entries, dict):
            entries = [entries]

        got_review = False
        for e in entries:
            if "im:rating" not in e:
                continue
            got_review = True

            body = (e.get("content", {}).get("label") or "").strip()
            if not body:
                continue

            rating = e.get("im:rating", {}).get("label", "?")
            tickets.append({
                "id": f"AS-{e.get('id', {}).get('label', str(len(tickets)))[-9:]}",
                "created_at": e.get("updated", {}).get("label", ""),
                "customer_name": e.get("author", {}).get("name", {}).get("label", "anonymous"),
                "company": app_name,
                "channel": f"appstore {rating}★",
                "subject": (e.get("title", {}).get("label") or body[:60]).strip(),
                "body": f"[{rating}/5 stars] {body}"[:2000],
            })
            if len(tickets) >= limit:
                break

        if not got_review:
            break
        page += 1

    return tickets
