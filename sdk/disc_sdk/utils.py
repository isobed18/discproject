"""Small helpers for the DISC SDK."""

from __future__ import annotations

import json
import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, Optional


def parse_iso_datetime_to_epoch(value: str) -> Optional[float]:
    """Parse an ISO-8601 datetime string into epoch seconds.

    Supports either timezone offsets ("+00:00") or a trailing "Z".
    Returns None if parsing fails.
    """

    if not value or not isinstance(value, str):
        return None

    s = value.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"

    try:
        dt = datetime.fromisoformat(s)
    except Exception:
        return None

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    return float(dt.timestamp())


def claims_expiry_epoch(claims: Dict[str, Any]) -> Optional[float]:
    """Extract `exp` from coupon claims and return it as epoch seconds."""

    exp = claims.get("exp")
    if isinstance(exp, (int, float)):
        return float(exp)
    if isinstance(exp, str):
        return parse_iso_datetime_to_epoch(exp)
    return None


def stable_cache_key(payload: Dict[str, Any]) -> str:
    """Create a stable, URL-safe cache key for a JSON-like dict."""

    try:
        s = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    except Exception:
        s = repr(payload)
    return hashlib.sha256(s.encode("utf-8")).hexdigest()
