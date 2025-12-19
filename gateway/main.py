"""HTTP Gateway / sidecar-style coupon validator (POC).

Week 3 deliverables implemented here:
 - Intercepts all inbound HTTP requests.
 - Extracts Authorization: Bearer <coupon>.
 - Calls Coupon Authority /v1/verify.
 - Enforces coupon validity and purpose-binding (method + path) before forwarding.
 - Forwards the same coupon (Authorization header) to upstream services.

Out of scope: gRPC interceptors.
"""

from __future__ import annotations

import os
import uuid
from contextlib import asynccontextmanager
from typing import Dict, Iterable, Optional, Set
from urllib.parse import urljoin

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response


HOP_BY_HOP_HEADERS = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
}


def _env_list(name: str, default: str) -> Set[str]:
    raw = os.getenv(name, default)
    return {item.strip() for item in raw.split(",") if item.strip()}


def _derive_purpose_candidates(method: str, path: str) -> Set[str]:
    """Derive purpose from HTTP request.

Spec says "method + path"; delimiter isn't specified.
To be robust (and still strict), we accept a small set of canonical encodings.
"""
    m = method.upper()
    p = path if path.startswith("/") else f"/{path}"
    return {
        f"{m} {p}",
        f"{m}:{p}",
        f"{m}+{p}",
        f"{m}{p}",
    }


def _parse_scopes(value: object) -> Set[str]:
    if value is None:
        return set()
    if isinstance(value, (list, tuple, set)):
        return {str(v).strip() for v in value if str(v).strip()}
    if isinstance(value, str):
        # allow common encodings: "a b", "a,b", "a; b"
        parts: Iterable[str]
        if "," in value:
            parts = value.split(",")
        elif ";" in value:
            parts = value.split(";")
        else:
            parts = value.split()
        return {p.strip() for p in parts if p.strip()}
    return {str(value).strip()} if str(value).strip() else set()


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


def _purpose_matches_claims(claims: Dict[str, object], candidates: Set[str]) -> bool:
    # "scope" is the primary claim in this repo; support a few common aliases.
    scope_val = claims.get("scope") or claims.get("scp") or claims.get("purpose") or claims.get("pur")
    scopes = _parse_scopes(scope_val)
    return bool(scopes.intersection(candidates))


def _filter_response_headers(headers: httpx.Headers) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for k, v in headers.items():
        if k.lower() in HOP_BY_HOP_HEADERS:
            continue
        out[k] = v
    return out


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Config
    app.state.ca_base_url = os.getenv("CA_BASE_URL", "http://localhost:8000/v1").rstrip("/")
    app.state.upstream_base_url = os.getenv("UPSTREAM_BASE_URL", "http://localhost:8001").rstrip("/")
    app.state.gateway_id = os.getenv("GATEWAY_ID", "disc-gateway")
    app.state.unprotected_paths = _env_list(
        "UNPROTECTED_PATHS",
        "/health,/ready,/live,/docs,/openapi.json",
    )
    timeout = float(os.getenv("GATEWAY_TIMEOUT_SECONDS", "10"))

    app.state.http = httpx.AsyncClient(timeout=timeout)
    try:
        yield
    finally:
        await app.state.http.aclose()


app = FastAPI(title="DISC Gateway (Week 3 POC)", lifespan=lifespan)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.middleware("http")
async def coupon_validation_middleware(request: Request, call_next):
    # Correlation ID propagation (traceability end-to-end)
    corr_id = request.headers.get("x-correlation-id") or request.headers.get("x-request-id") or str(uuid.uuid4())
    request.state.correlation_id = corr_id

    # Intercept all inbound requests.
    if request.url.path in request.app.state.unprotected_paths:
        resp = await call_next(request)
        resp.headers["x-correlation-id"] = corr_id
        return resp

    coupon = _extract_coupon(request)
    if not coupon:
        return JSONResponse(status_code=401, content={"detail": "missing_coupon"})

    verify_url = urljoin(f"{request.app.state.ca_base_url}/", "verify")

    try:
        verify_resp = await request.app.state.http.post(
            verify_url,
            json={"coupon": coupon},
            headers={
                "x-correlation-id": corr_id,
                "x-gateway-id": request.app.state.gateway_id,
                "x-actor": "gateway",
            },
        )
    except Exception:
        return JSONResponse(status_code=503, content={"detail": "coupon_authority_unavailable"})

    if verify_resp.status_code != 200:
        return JSONResponse(
            status_code=503,
            content={"detail": "coupon_authority_error", "status_code": verify_resp.status_code},
        )

    try:
        data = verify_resp.json()
    except Exception:
        return JSONResponse(status_code=503, content={"detail": "coupon_authority_bad_response"})

    if not data.get("valid"):
        return JSONResponse(status_code=403, content={"detail": "invalid_coupon", "error": data.get("error")})

    claims = data.get("claims") or {}

    # Purpose binding enforcement at gateway level.
    candidates = _derive_purpose_candidates(request.method, request.url.path)
    if not _purpose_matches_claims(claims, candidates):
        return JSONResponse(
            status_code=403,
            content={
                "detail": "purpose_mismatch",
                "expected": sorted(candidates),
                "scope": claims.get("scope"),
            },
        )

    # Store for downstream handlers if needed.
    request.state.coupon = coupon
    request.state.coupon_claims = claims

    resp = await call_next(request)
    resp.headers["x-correlation-id"] = corr_id
    return resp


@app.api_route("/{full_path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"])
async def proxy_to_upstream(full_path: str, request: Request):
    """Forward request to upstream service after coupon validation.

    Outbound requirement: forward the *same coupon* to upstream.
    (Inbound middleware already validated it.)
    """
    upstream_url = urljoin(f"{request.app.state.upstream_base_url}/", full_path)
    if request.url.query:
        upstream_url = f"{upstream_url}?{request.url.query}"

    # Forward most headers. (Keep Authorization to satisfy outbound propagation.)
    headers = {k: v for k, v in request.headers.items() if k.lower() not in {"host", "content-length"}}
    # Ensure correlation id and gateway id are always forwarded.
    corr_id = getattr(request.state, "correlation_id", None) or request.headers.get("x-correlation-id")
    if corr_id:
        headers["x-correlation-id"] = corr_id
    headers["x-gateway-id"] = request.app.state.gateway_id

    body = await request.body()

    try:
        upstream_resp = await request.app.state.http.request(
            method=request.method,
            url=upstream_url,
            headers=headers,
            content=body,
        )
    except Exception:
        return JSONResponse(status_code=502, content={"detail": "upstream_unavailable"})

    return Response(
        content=upstream_resp.content,
        status_code=upstream_resp.status_code,
        headers=_filter_response_headers(upstream_resp.headers),
        media_type=upstream_resp.headers.get("content-type"),
    )
