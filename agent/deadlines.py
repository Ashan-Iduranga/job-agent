"""Parse the many date formats job sites use into ISO dates."""
from __future__ import annotations

import re
from datetime import date, timedelta

from dateutil import parser as dparser

_RELATIVE = re.compile(r"(\d+)\s+(day|week|month)s?\s+ago", re.I)


def parse_date(text: str | None, today: date | None = None) -> str | None:
    """Return an ISO date (YYYY-MM-DD) or None. Day-first for numeric dates (Sri Lankan style)."""
    if not text:
        return None
    s = text.strip()
    if not s:
        return None
    today = today or date.today()
    low = s.lower()
    if low in {"today", "just now"}:
        return today.isoformat()
    if low == "yesterday":
        return (today - timedelta(days=1)).isoformat()
    m = _RELATIVE.search(low)
    if m:
        n, unit = int(m.group(1)), m.group(2).lower()
        days = n * {"day": 1, "week": 7, "month": 30}[unit]
        return (today - timedelta(days=days)).isoformat()
    try:
        if re.match(r"\d{4}-\d{1,2}-\d{1,2}", s):  # ISO: never day-first
            return date.fromisoformat(s[:10]).isoformat()
        return dparser.parse(s, dayfirst=True, fuzzy=True).date().isoformat()
    except (ValueError, OverflowError):
        return None


def days_until(iso: str | None, today: date | None = None) -> int | None:
    """Days from today until an ISO date (negative if past)."""
    if not iso:
        return None
    today = today or date.today()
    return (date.fromisoformat(iso) - today).days
