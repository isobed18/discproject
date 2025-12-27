"""TTL cache built on top of :mod:`disc_sdk.storage`.

Week 5 requirement: local cache.

The cache stores entries as JSON dicts with an absolute expiry time.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

from .storage import Storage


def _now() -> float:
    return time.time()


@dataclass
class CacheEntry:
    value: Dict[str, Any]
    expires_at: float
    created_at: float


class DiscCache:
    """A tiny TTL cache for the SDK."""

    def __init__(self, storage: Storage, *, namespace: str = "disc_sdk") -> None:
        self._storage = storage
        self._ns = namespace

    def _k(self, key: str) -> str:
        return f"{self._ns}:{key}"

    def get(self, key: str) -> Optional[CacheEntry]:
        raw = self._storage.get(self._k(key))
        if not raw:
            return None
        try:
            expires_at = float(raw.get("expires_at", 0))
            created_at = float(raw.get("created_at", 0))
            value = raw.get("value")
            if not isinstance(value, dict):
                return None
        except Exception:
            return None

        if expires_at <= _now():
            self.delete(key)
            return None
        return CacheEntry(value=value, expires_at=expires_at, created_at=created_at)

    def set(self, key: str, value: Dict[str, Any], *, ttl_seconds: float) -> None:
        ttl_seconds = max(float(ttl_seconds), 0.0)
        expires_at = _now() + ttl_seconds
        self._storage.set(
            self._k(key),
            {"value": value, "expires_at": expires_at, "created_at": _now()},
        )

    def delete(self, key: str) -> None:
        self._storage.delete(self._k(key))
