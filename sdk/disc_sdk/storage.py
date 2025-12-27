"""Storage backends for the DISC SDK.

Week 5 requirement: *Configurable storage implementation*.

The SDK uses storage to persist a small local cache (verification results,
public key material, etc.) to improve resilience and developer experience.

The cache layer stores TTL metadata itself, so storage only needs to support
basic get/set/delete operations for JSON-serializable values.
"""

from __future__ import annotations

import json
import os
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Protocol


class Storage(Protocol):
    """A minimal key/value storage protocol for the SDK."""

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        ...

    def set(self, key: str, value: Dict[str, Any]) -> None:
        ...

    def delete(self, key: str) -> None:
        ...


@dataclass
class InMemoryStorage:
    """Thread-safe in-memory storage (default)."""

    _data: Dict[str, Dict[str, Any]]

    def __init__(self) -> None:
        self._data = {}
        self._lock = threading.RLock()

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            v = self._data.get(key)
            return dict(v) if isinstance(v, dict) else None

    def set(self, key: str, value: Dict[str, Any]) -> None:
        with self._lock:
            self._data[key] = dict(value)

    def delete(self, key: str) -> None:
        with self._lock:
            self._data.pop(key, None)


class FileStorage:
    """JSON-file backed storage.

    This is intended for local dev/CLI usage. It is *not* a database.
    Writes are atomic via `os.replace()`.
    """

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path).expanduser()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()

    def _read_all(self) -> Dict[str, Any]:
        if not self.path.exists():
            return {}
        try:
            raw = self.path.read_text(encoding="utf-8")
            if not raw.strip():
                return {}
            data = json.loads(raw)
            return data if isinstance(data, dict) else {}
        except Exception:
            # Corrupt cache should not break SDK usage.
            return {}

    def _write_all(self, data: Dict[str, Any]) -> None:
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, self.path)

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            data = self._read_all()
            v = data.get(key)
            return dict(v) if isinstance(v, dict) else None

    def set(self, key: str, value: Dict[str, Any]) -> None:
        with self._lock:
            data = self._read_all()
            data[key] = value
            self._write_all(data)

    def delete(self, key: str) -> None:
        with self._lock:
            data = self._read_all()
            data.pop(key, None)
            self._write_all(data)


class NullStorage:
    """A no-op storage backend (disables persistence)."""

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        return None

    def set(self, key: str, value: Dict[str, Any]) -> None:
        return None

    def delete(self, key: str) -> None:
        return None
