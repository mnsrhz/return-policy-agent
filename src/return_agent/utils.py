from __future__ import annotations

import re
from datetime import date, datetime
from typing import Iterable, Optional


def parse_date(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    if isinstance(value, date):
        return value
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%B %d, %Y"):
        try:
            return datetime.strptime(str(value), fmt).date()
        except ValueError:
            continue
    return None


def days_since(value: Optional[str], today: Optional[date] = None) -> Optional[int]:
    parsed = parse_date(value)
    if not parsed:
        return None
    today = today or date.today()
    return (today - parsed).days


def contains_any(text: str, terms: Iterable[str]) -> bool:
    lowered = text.lower()
    return any(term in lowered for term in terms)


def condition_is_eligible(condition: Optional[str]) -> bool:
    if not condition:
        return False
    lowered = condition.lower()
    disallowed_patterns = [
        r"\bused\b",
        r"\bworn\b",
        r"\bwashed\b",
        r"\bmissing\s+packaging\b",
        r"\bdamaged\b",
    ]
    if any(re.search(pattern, lowered) for pattern in disallowed_patterns):
        return False
    return any(term in lowered for term in ["unused", "unworn", "unwashed", "original packaging"])
