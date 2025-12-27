from __future__ import annotations

import os
import time
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urljoin

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response

from .base import GatewayContext


def _extract_coupon(request: Request) -> Optional[str]:
    auth = request.headers.get("authorization")
    if not auth:
        return None
    parts = auth.split(None, 1)
    if len(parts) != 2:
        return None
    scheme, token = parts[0], parts[1]
    if scheme.lower() != "bearer":
        return None
    token = token.strip()
    return token or None


def _parse_exp_to_epoch(exp: object) -> Optional[float]:
    from datetime import datetime, timezone

    if isinstance(exp, (int, float)):
        return float(exp)
    if isinstance(exp, str):
        s = exp.strip()
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        try:
            dt = datetime.fromisoformat(s)
        except Exception:
            return None
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return float(dt.timestamp())
    return None


class VerifyWithCAPlugin:
    """Verify coupons by calling the Coupon Authority.

    Optional offline cache fallback:
    - Set GATEWAY_OFFLINE_CACHE=1 to allow returning a cached valid verification
      if the CA is unreachable.
    """

    def __init__(self, app: FastAPI) -> None:
        self.app = app
        self.retries = int(os.getenv("GATEWAY_VERIFY_RETRIES", "2"))
        self.backoff = float(os.getenv("GATEWAY_VERIFY_BACKOFF", "0.25"))
        self.offline_cache = os.getenv("GATEWAY_OFFLINE_CACHE", "0").lower() in {"1", "true", "yes"}
        self._cache: Dict[str, Tuple[Dict[str, Any], float]] = {}  # token -> (claims, exp_epoch)

    async def _post_with_retry(self, url: str, *, json: Dict[str, Any], headers: Dict[str, str]) -> httpx.Response:
        last_exc: Optional[Exception] = None
        for attempt in range(self.retries + 1):
            try:
                resp = await self.app.state.http.post(url, json=json, headers=headers)
                if resp.status_code in {429, 500, 502, 503, 504} and attempt < self.retries:
                    delay = min(4.0, self.backoff * (2**attempt))
                    await asyncio.sleep(delay)
                    continue
                return resp
            except Exception as e:
                last_exc = e
                if attempt < self.retries:
                    delay = min(4.0, self.backoff * (2**attempt))
                    await asyncio.sleep(delay)
                    continue
                raise
        if last_exc:
            raise last_exc
        raise RuntimeError("verify request failed")

    async def process(self, request: Request, ctx: GatewayContext) -> Optional[Response]:
        coupon = _extract_coupon(request)
        if not coupon:
            return JSONResponse(status_code=401, content={"detail": "missing_coupon"})

        ctx.coupon = coupon

        verify_url = urljoin(f"{request.app.state.ca_base_url}/", "verify")

        headers = {
            "x-correlation-id": ctx.correlation_id,
            "x-gateway-id": request.app.state.gateway_id,
            "x-actor": "gateway",
        }

        try:
            resp = await self._post_with_retry(verify_url, json={"coupon": coupon}, headers=headers)
        except Exception:
            # Offline cache fallback if enabled.
            if self.offline_cache:
                cached = self._cache.get(coupon)
                if cached:
                    claims, exp_epoch = cached
                    if exp_epoch > time.time():
                        ctx.claims = claims
                        request.state.coupon = coupon
                        request.state.coupon_claims = claims
                        return None
            return JSONResponse(status_code=503, content={"detail": "coupon_authority_unavailable"})

        if resp.status_code != 200:
            return JSONResponse(
                status_code=503,
                content={"detail": "coupon_authority_error", "status_code": resp.status_code},
            )

        try:
            data = resp.json()
        except Exception:
            return JSONResponse(status_code=503, content={"detail": "coupon_authority_bad_response"})

        if not data.get("valid"):
            return JSONResponse(status_code=403, content={"detail": "invalid_coupon", "error": data.get("error")})

        claims = data.get("claims") or {}
        if not isinstance(claims, dict):
            claims = {}

        ctx.claims = claims
        request.state.coupon = coupon
        request.state.coupon_claims = claims

        # Cache valid verifications.
        if self.offline_cache:
            exp_epoch = _parse_exp_to_epoch(claims.get("exp"))
            if exp_epoch is None:
                exp_epoch = time.time() + 60
            self._cache[coupon] = (claims, exp_epoch)

        return None


import asyncio  # noqa: E402
