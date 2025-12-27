from __future__ import annotations

"""Purpose binding enforcement plugin.

Week 3 requirement: enforce method+path binding at gateway.

This was previously embedded in gateway/main.py. It is now a plugin.
"""

from typing import Iterable, Optional, Set

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response

from .base import GatewayContext


def _derive_purpose_candidates(method: str, path: str) -> Set[str]:
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
        parts: Iterable[str]
        if "," in value:
            parts = value.split(",")
        elif ";" in value:
            parts = value.split(";")
        else:
            parts = value.split()
        return {p.strip() for p in parts if p.strip()}
    return {str(value).strip()} if str(value).strip() else set()


def _purpose_matches_claims(claims: dict, candidates: Set[str]) -> bool:
    scope_val = claims.get("scope") or claims.get("scp") or claims.get("purpose") or claims.get("pur")
    scopes = _parse_scopes(scope_val)
    return bool(scopes.intersection(candidates))


class PurposeBindingPlugin:
    def __init__(self, app: FastAPI) -> None:
        self.app = app

    async def process(self, request: Request, ctx: GatewayContext) -> Optional[Response]:
        claims = ctx.claims or {}
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
        return None
