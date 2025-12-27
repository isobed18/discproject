"""HTTP Gateway / sidecar-style coupon validator.

Originally implemented as a single-file POC (Week 3). Week 5/6 backlog asked
for *Gateway pluginization*, so the validation logic is now a configurable
plugin pipeline.

Default pipeline:
  1) VerifyWithCAPlugin   - calls /v1/verify on the Coupon Authority
  2) PurposeBindingPlugin - enforces method+path binding

Configure plugins via env var:
  GATEWAY_PLUGINS=module:Class,module:Class

Other config:
  CA_BASE_URL, UPSTREAM_BASE_URL, UNPROTECTED_PATHS, GATEWAY_TIMEOUT_SECONDS
"""

from __future__ import annotations

import os
import uuid
from contextlib import asynccontextmanager
from typing import Dict, Optional, Set
from urllib.parse import urljoin

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response

from .plugins import GatewayContext, load_plugins


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


def _filter_response_headers(headers: httpx.Headers) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for k, v in headers.items():
        if k.lower() in HOP_BY_HOP_HEADERS:
            continue
        out[k] = v
    return out


def create_app() -> FastAPI:
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
        app.state.plugins = load_plugins(app)
        try:
            yield
        finally:
            await app.state.http.aclose()

    app = FastAPI(title="DISC Gateway", lifespan=lifespan)

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    @app.middleware("http")
    async def coupon_validation_middleware(request: Request, call_next):
        # Correlation ID propagation (traceability end-to-end)
        corr_id = request.headers.get("x-correlation-id") or request.headers.get("x-request-id") or str(uuid.uuid4())
        request.state.correlation_id = corr_id

        # Allow unprotected paths (health/docs)
        if request.url.path in request.app.state.unprotected_paths:
            resp = await call_next(request)
            resp.headers["x-correlation-id"] = corr_id
            return resp

        ctx = GatewayContext(correlation_id=corr_id)
        for plugin in request.app.state.plugins:
            maybe_resp = await plugin.process(request, ctx)
            if maybe_resp is not None:
                maybe_resp.headers["x-correlation-id"] = corr_id
                return maybe_resp

        # Store for downstream handlers if needed.
        request.state.coupon = ctx.coupon
        request.state.coupon_claims = ctx.claims

        resp = await call_next(request)
        resp.headers["x-correlation-id"] = corr_id
        return resp

    @app.api_route("/{full_path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"])
    async def proxy_to_upstream(full_path: str, request: Request):
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

    return app


app = create_app()
