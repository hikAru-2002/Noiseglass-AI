"""
Normalizes user-uploaded ticket data (CSV or pasted free text) into the same
ticket shape the rest of the pipeline already expects:
  { id, created_at, customer_name, company, channel, subject, body }

This is intentionally permissive: real customer data will never be as clean
as our synthetic dataset, so we fill in sensible defaults for anything
missing rather than rejecting the upload outright.
"""

import csv
import io
from datetime import datetime, timezone
from typing import Optional


REQUIRED_TEXT_FIELDS = ("body", "text", "description", "message", "ticket", "content")
DATE_FIELDS = ("created_at", "date", "created", "timestamp")
SUBJECT_FIELDS = ("subject", "title", "summary")
CUSTOMER_FIELDS = ("customer_name", "customer", "name", "requester")
COMPANY_FIELDS = ("company", "organization", "account")
CHANNEL_FIELDS = ("channel", "source")


def _first_present(row: dict, candidates: tuple, default: str = "") -> str:
    for key in candidates:
        for actual_key in row:
            if actual_key.strip().lower() == key:
                val = row[actual_key]
                if val and str(val).strip():
                    return str(val).strip()
    return default


def _parse_date(raw: str) -> str:
    """Best-effort parse of a date string into an ISO timestamp. Falls back
    to now() if unparseable, so a bad date never breaks the whole upload."""
    if not raw:
        return datetime.now(timezone.utc).isoformat()
    raw = raw.strip()
    formats = [
        "%Y-%m-%d",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%m/%d/%Y",
        "%m/%d/%Y %H:%M",
        "%d/%m/%Y",
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(raw, fmt)
            return dt.replace(tzinfo=timezone.utc).isoformat()
        except ValueError:
            continue
    # last resort: try isoformat directly (handles already-ISO strings, incl. "Z")
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).isoformat()
    except ValueError:
        return datetime.now(timezone.utc).isoformat()


def parse_csv_tickets(csv_text: str) -> list[dict]:
    """Parse uploaded CSV text into normalized ticket dicts.
    Expects a header row; column names are matched case-insensitively
    against several common aliases (see *_FIELDS above)."""
    reader = csv.DictReader(io.StringIO(csv_text))
    tickets = []
    for i, row in enumerate(reader):
        body = _first_present(row, REQUIRED_TEXT_FIELDS)
        if not body:
            continue  # skip rows with no usable ticket text
        subject = _first_present(row, SUBJECT_FIELDS) or body[:60]
        tickets.append(
            {
                "id": f"UPL-{i + 1:04d}",
                "created_at": _parse_date(_first_present(row, DATE_FIELDS)),
                "customer_name": _first_present(row, CUSTOMER_FIELDS, "Unknown"),
                "company": _first_present(row, COMPANY_FIELDS, "Unknown"),
                "channel": _first_present(row, CHANNEL_FIELDS, "upload") or "upload",
                "subject": subject,
                "body": body,
            }
        )
    return tickets


def parse_pasted_tickets(text: str) -> list[dict]:
    """Parse freeform pasted text into normalized ticket dicts, one ticket
    per non-empty line. No customer/company/date metadata is available, so
    all tickets are stamped with the current time (they'll all land in the
    'this week' bucket, which is the honest reflection of what we know)."""
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    now_iso = datetime.now(timezone.utc).isoformat()
    tickets = []
    for i, line in enumerate(lines):
        tickets.append(
            {
                "id": f"PST-{i + 1:04d}",
                "created_at": now_iso,
                "customer_name": "Unknown",
                "company": "Unknown",
                "channel": "upload",
                "subject": line[:60],
                "body": line,
            }
        )
    return tickets
