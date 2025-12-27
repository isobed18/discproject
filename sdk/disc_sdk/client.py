"""DISC SDK client.

Week 5 deliverables:
- Retry/backoff (for all HTTP operations)
- Local cache
- Configurable storage implementation
- SDK offline mode

Offline mode behavior (default):
- If the Coupon Authority is unreachable, `verify_coupon()` can fall back to
  cached verification results (when present and not expired).
- `issue_coupon()` can optionally fall back to a cached coupon for the same
  request (audience/scope/ttl) if it is still valid.

Security note:
Offline verification via cache is a DX/resilience feature; it does *not* replace
proper local cryptographic verification. For true offline verification, provide
`public_key_pem` (or enable `auto_fetch_public_key`) and set
`offline_strategy="local"`.
"""

from __future__ import annotations

import logging
import random
import time
from typing import Any, Dict, Mapping, Optional, Set, Callable

import httpx

try:
    import pyseto
    from pyseto import Key
except Exception:  # pragma: no cover
    pyseto = None
    Key = None

from .cache import DiscCache
from .storage import InMemoryStorage, Storage
from .utils import claims_expiry_epoch, stable_cache_key

logger = logging.getLogger("disc_sdk")


class DiscClient:
    """Lightweight DISC SDK client."""

    def __init__(
        self,
        base_url: str = "http://localhost:8000/v1",
        *,
        tracing_headers: Optional[Mapping[str, str]] = None,
        timeout_seconds: float = 10.0,
        max_retries: int = 3,
        backoff_factor: float = 0.5,
        backoff_max_seconds: float = 8.0,
        retry_status_codes: Optional[Set[int]] = None,
        cache: bool = True,
        storage: Optional[Storage] = None,
        cache_namespace: str = "disc_sdk",
        offline: bool = False,
        offline_strategy: str = "cache",  # "cache" | "local" | "auto" | "none"
        public_key_pem: Optional[str] = None,
        auto_fetch_public_key: bool = False,
        revocation_checker: Optional[Callable[[str], bool]] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self._tracing_headers: Dict[str, str] = dict(tracing_headers or {})
        self.client = httpx.Client(base_url=self.base_url, timeout=timeout_seconds)

        self.max_retries = max(0, int(max_retries))
        self.backoff_factor = float(backoff_factor)
        self.backoff_max_seconds = float(backoff_max_seconds)
        self.retry_status_codes: Set[int] = set(retry_status_codes or {429, 500, 502, 503, 504})

        self.offline = bool(offline)
        self.offline_strategy = offline_strategy

        self._revocation_checker = revocation_checker

        self._storage = storage or InMemoryStorage()
        self._cache = DiscCache(self._storage, namespace=cache_namespace) if cache else None

        self._public_key_pem = public_key_pem
        self._auto_fetch_public_key = bool(auto_fetch_public_key)

    def close(self) -> None:
        self.client.close()

    def __enter__(self) -> "DiscClient":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def _merge_headers(self, headers: Optional[Mapping[str, str]] = None) -> Dict[str, str]:
        merged: Dict[str, str] = {}
        merged.update(self._tracing_headers)
        if headers:
            merged.update(dict(headers))
        return merged

    def _compute_backoff_seconds(self, attempt: int) -> float:
        # Exponential backoff with jitter.
        base = self.backoff_factor * (2 ** attempt)
        jitter = random.uniform(0, 0.25 * base) if base > 0 else 0.0
        return min(self.backoff_max_seconds, base + jitter)

    def _request_with_retry(self, method: str, url: str, **kwargs) -> httpx.Response:
        """Internal wrapper to handle retries for transient errors."""

        last_exception: Optional[Exception] = None
        for attempt in range(self.max_retries + 1):
            try:
                resp = self.client.request(method, url, **kwargs)
                if resp.status_code in self.retry_status_codes:
                    # Respect Retry-After if present.
                    retry_after = resp.headers.get("retry-after")
                    if retry_after and retry_after.isdigit():
                        delay = min(self.backoff_max_seconds, float(retry_after))
                    else:
                        delay = self._compute_backoff_seconds(attempt)
                    if attempt < self.max_retries:
                        logger.warning(
                            "Request %s %s returned %s; retrying in %.2fs",
                            method,
                            url,
                            resp.status_code,
                            delay,
                        )
                        time.sleep(delay)
                        continue
                return resp
            except (httpx.ConnectError, httpx.ReadTimeout, httpx.WriteTimeout, httpx.RemoteProtocolError) as e:
                last_exception = e
                if attempt < self.max_retries:
                    delay = self._compute_backoff_seconds(attempt)
                    logger.warning("Request %s %s failed (%s); retrying in %.2fs", method, url, e, delay)
                    time.sleep(delay)
                    continue
                break

        if last_exception:
            raise last_exception
        raise httpx.RequestError("request failed")

    # ---- Public key support (for local/offline verification) ----
    def _public_key_cache_key(self) -> str:
        return "public_key"

    def get_public_key_pem(self, *, headers: Optional[Mapping[str, str]] = None) -> str:
        """Fetch public key PEM from the CA (and cache it).

        Requires the backend endpoint: GET /v1/public-key.
        """

        if self._public_key_pem:
            return self._public_key_pem

        if self._cache:
            cached = self._cache.get(self._public_key_cache_key())
            if cached and isinstance(cached.value.get("pem"), str):
                return cached.value["pem"]

        resp = self._request_with_retry("GET", "/public-key", headers=self._merge_headers(headers))
        resp.raise_for_status()
        pem = resp.json().get("public_key_pem")
        if not isinstance(pem, str) or not pem.strip():
            raise ValueError("invalid public key response")
        self._public_key_pem = pem
        if self._cache:
            self._cache.set(self._public_key_cache_key(), {"pem": pem}, ttl_seconds=3600)
        return pem

    def _local_verify(self, token: str) -> Dict[str, Any]:
        if pyseto is None or Key is None:
            raise RuntimeError("pyseto is required for local verification")

        pem = self._public_key_pem
        if (not pem) and self._auto_fetch_public_key:
            pem = self.get_public_key_pem()
        if not pem:
            raise RuntimeError("public_key_pem is not configured")

        key = Key.new(version=4, purpose="public", key=pem.encode("utf-8"))
        decoded = pyseto.decode(key, token)
        # pyseto returns payload bytes; it is JSON from our backend.
        import json

        claims = json.loads(decoded.payload)

        # Basic exp check (backend also checks on server). Fail closed.
        exp_epoch = claims_expiry_epoch(claims)
        if exp_epoch is not None and exp_epoch <= time.time():
            raise ValueError("expired")

        # Optional revocation check.
        if self._revocation_checker:
            jti = claims.get("jti")
            if isinstance(jti, str) and jti and self._revocation_checker(jti):
                raise ValueError("revoked")

        return claims

    # ---- Core operations ----
    def issue_coupon(
        self,
        audience: str,
        scope: str,
        ttl_seconds: int = 300,
        *,
        headers: Optional[Mapping[str, str]] = None,
        allow_cache_fallback: bool = True,
    ) -> Dict[str, Any]:
        """Issue a new coupon.

        If `offline=True` and the CA is unreachable, optionally return the last
        cached successful issuance for the same (audience, scope, ttl) provided
        it is still valid.
        """

        cache_key = None
        if self._cache:
            cache_key = f"issue:{stable_cache_key({'audience': audience, 'scope': scope, 'ttl': int(ttl_seconds)})}"

        try:
            resp = self._request_with_retry(
                "POST",
                "/issue",
                json={"audience": audience, "scope": scope, "ttl_seconds": int(ttl_seconds)},
                headers=self._merge_headers(headers),
            )
            resp.raise_for_status()
            data = resp.json()

            if self._cache and cache_key and isinstance(data, dict) and isinstance(data.get("coupon"), str):
                # Cache until coupon expiry when possible.
                expires_in = data.get("expires_in")
                ttl = float(expires_in) if isinstance(expires_in, (int, float)) else float(ttl_seconds)
                ttl = max(ttl, 1.0)
                self._cache.set(cache_key, {"response": data}, ttl_seconds=ttl)
            return data
        except Exception as e:
            if self.offline and allow_cache_fallback and self._cache and cache_key:
                cached = self._cache.get(cache_key)
                if cached and isinstance(cached.value.get("response"), dict):
                    out = dict(cached.value["response"])
                    out["cached"] = True
                    out["cached_reason"] = "offline_issue_fallback"
                    return out
            raise e

    def verify_coupon(
        self,
        coupon: str,
        *,
        headers: Optional[Mapping[str, str]] = None,
        cache_results: bool = True,
    ) -> Dict[str, Any]:
        """Verify a coupon.

        Strategy:
        - Try CA /verify.
        - Cache successful results locally (default).
        - If CA is unreachable and offline mode is enabled:
            - offline_strategy="cache": return cached result if present
            - offline_strategy="local": perform local cryptographic verification
            - offline_strategy="auto": try local, then cache
        """

        cache_key = None
        if self._cache:
            cache_key = f"verify:{stable_cache_key({'coupon': coupon})}"

        try:
            resp = self._request_with_retry(
                "POST",
                "/verify",
                json={"coupon": coupon},
                headers=self._merge_headers(headers),
            )
            resp.raise_for_status()
            data = resp.json()
            if not isinstance(data, dict):
                raise ValueError("invalid verify response")

            # Cache only valid results by default.
            if self._cache and cache_results and data.get("valid") is True and isinstance(data.get("claims"), dict):
                exp_epoch = claims_expiry_epoch(data["claims"])  # type: ignore[index]
                if exp_epoch is not None:
                    ttl = max(exp_epoch - time.time(), 1.0)
                else:
                    ttl = 60.0
                self._cache.set(cache_key, {"response": data}, ttl_seconds=ttl)
            return data
        except Exception as e:
            if not self.offline:
                raise e

            strategy = (self.offline_strategy or "cache").lower()
            if strategy not in {"cache", "local", "auto", "none"}:
                strategy = "cache"

            # Try local crypto verification first if requested.
            if strategy in {"local", "auto"}:
                try:
                    claims = self._local_verify(coupon)
                    return {"valid": True, "claims": claims, "offline": True, "source": "local"}
                except Exception as le:
                    logger.debug("Local verification failed: %s", le)
                    if strategy == "local":
                        raise e

            # Cache fallback.
            if strategy in {"cache", "auto"} and self._cache and cache_key:
                cached = self._cache.get(cache_key)
                if cached and isinstance(cached.value.get("response"), dict):
                    out = dict(cached.value["response"])
                    out["offline"] = True
                    out["source"] = "cache"
                    out["cached_reason"] = "offline_verify_fallback"
                    return out

            raise e

    def revoke_coupon(
        self,
        jti: str,
        reason: str = "unspecified",
        *,
        headers: Optional[Mapping[str, str]] = None,
    ) -> Dict[str, Any]:
        """Revoke a coupon."""

        resp = self._request_with_retry(
            "POST",
            "/revoke",
            json={"jti": jti, "reason": reason},
            headers=self._merge_headers(headers),
        )
        resp.raise_for_status()
        return resp.json()
