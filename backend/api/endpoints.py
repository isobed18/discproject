from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, Header, HTTPException, Request, Query

from .models import (
    CouponRequest,
    CouponResponse,
    VerifyRequest,
    VerifyResponse,
    RevokeRequest,
    RevokeResponse,
    DelegationRequest,
    PartialEvalRequest,
)

from core.security import create_coupon, verify_coupon, verify_oidc_token, get_mtls_identity
from services.revocation import revoke_jti, is_jti_revoked
from services.delegation import add_delegation, get_delegations_for_resource
from services.audit import audit_service
from services.audit_store import audit_store
from core.metrics import (
    COUPON_ISSUE_TOTAL,
    COUPON_VERIFY_TOTAL,
    COUPON_REVOKE_TOTAL,
    ISSUE_LATENCY_SECONDS,
    VERIFY_LATENCY_SECONDS,
    REVOKE_LATENCY_SECONDS,
    LAST_REVOKE_TS,
    now_unix,
    OPA_DENY_TOTAL,
    OPA_UNAVAILABLE_TOTAL,
)
from core.policy import policy_engine

# Week 5: Rate Limiting
from slowapi import _rate_limit_exceeded_handler
from core.limiter import limiter

router = APIRouter()


def _correlation_id(request: Request) -> Optional[str]:
    return getattr(request.state, "correlation_id", None)


def _extract_gateway_info(request: Request) -> Dict[str, Any]:
    headers = request.headers
    return {
        "gateway_id": headers.get("x-gateway-id"),
        "forwarded_for": headers.get("x-forwarded-for") or headers.get("x-real-ip"),
        "via": headers.get("via"),
        "user_agent": headers.get("user-agent"),
    }


def _extract_request_info(request: Request) -> Dict[str, Any]:
    client_ip = None
    try:
        if request.client:
            client_ip = request.client.host
    except Exception:
        pass

    return {
        "method": request.method,
        "path": request.url.path,
        "query": request.url.query,
        "client_ip": client_ip,
        "host": request.headers.get("host"),
        "user_agent": request.headers.get("user-agent"),
    }


def _resolve_actor(authorization: Optional[str], fallback: str = "anonymous") -> str:
    user_id = fallback
    if authorization:
        try:
            scheme, token = authorization.split()
            if scheme.lower() == "bearer":
                claims = verify_oidc_token(token)
                user_id = claims.get("sub", "unknown")
        except Exception:
            pass
    return user_id


@router.post("/delegations")
async def create_delegation(req: DelegationRequest):
    # Week 3: Delegation Creation
    add_delegation("owner", req.delegate, req.resource, req.ttl)
    return {"status": "delegation_created", "delegate": req.delegate, "resource": req.resource}


@router.post("/issue", response_model=CouponResponse)
@limiter.limit("5/minute")
async def issue_coupon(
    req: CouponRequest,
    request: Request,
    authorization: Optional[str] = Header(None),
):
    with ISSUE_LATENCY_SECONDS.time():
        corr = _correlation_id(request)
        user_id = _resolve_actor(authorization, fallback="anonymous")

        # mTLS Identity
        mtls_id = get_mtls_identity(request.headers)

        # POLICY CHECK (Week 3 - OPA)
        delegated_users = []
        if req.resource:
            delegated_users = get_delegations_for_resource(req.resource)

        policy_input = {
            "audience": req.audience,
            "scope": req.scope,
            "token": {"sub": user_id, "aud": req.audience, "scope": req.scope},
            "delegations": {req.resource if req.resource else "global": delegated_users},
            "resource": req.resource,
        }

        try:
            allowed = policy_engine.check_permission(policy_input)
        except Exception:
            OPA_UNAVAILABLE_TOTAL.inc()
            await audit_service.log_event(
                event_type="opa_unavailable",
                actor=user_id,
                action="issue",
                resource=req.resource or "none",
                details={"audience": req.audience, "scope": req.scope},
                correlation_id=corr,
                gateway=_extract_gateway_info(request),
                request=_extract_request_info(request),
            )
            raise HTTPException(status_code=503, detail="OPA unavailable")

        if not allowed:
            OPA_DENY_TOTAL.inc()
            await audit_service.log_event(
                event_type="coupon_issue_denied",
                actor=user_id,
                action="issue",
                resource=req.resource or "none",
                details={"audience": req.audience, "scope": req.scope, "reason": "policy_denied"},
                correlation_id=corr,
                gateway=_extract_gateway_info(request),
                request=_extract_request_info(request),
            )
            raise HTTPException(status_code=403, detail="Policy denied by OPA")

        # CREATE COUPON
        cnf = {"x5t#S256": mtls_id.split(":")[1]} if mtls_id else None
        token = create_coupon(
            subject=user_id,
            audience=req.audience,
            scope=req.scope,
            ttl_seconds=req.ttl_seconds or 300,
            cnf=cnf,
        )

        decoded = verify_coupon(token)
        jti = decoded.get("jti")

        await audit_service.log_event(
            event_type="coupon_issued",
            actor=user_id,
            action="issue",
            resource=jti,
            details={
                "audience": req.audience,
                "scope": req.scope,
                "resource": req.resource,
                "mtls": bool(mtls_id),
            },
            correlation_id=corr,
            gateway=_extract_gateway_info(request),
            request=_extract_request_info(request),
        )

        COUPON_ISSUE_TOTAL.inc()
        return CouponResponse(coupon=token, expires_in=req.ttl_seconds or 300, jti=jti)


@router.post("/verify", response_model=VerifyResponse)
async def verify_token(
    req: VerifyRequest,
    request: Request,
    authorization: Optional[str] = Header(None),
    x_actor: Optional[str] = Header(None),
):
    with VERIFY_LATENCY_SECONDS.time():
        corr = _correlation_id(request)
        actor = x_actor or _resolve_actor(authorization, fallback="unknown")
        try:
            claims = verify_coupon(req.coupon)
            jti = claims.get("jti")

            if jti and is_jti_revoked(jti):
                await audit_service.log_event(
                    "coupon_verify_failed",
                    actor,
                    "verify",
                    jti,
                    {"reason": "revoked"},
                    correlation_id=corr,
                    gateway=_extract_gateway_info(request),
                    request=_extract_request_info(request),
                )
                return VerifyResponse(valid=False, error="revoked")

            # Week 4: log successful verifies too (for traceability)
            await audit_service.log_event(
                "coupon_verified",
                actor,
                "verify",
                jti or "unknown",
                {"valid": True, "aud": claims.get("aud"), "scope": claims.get("scope")},
                correlation_id=corr,
                gateway=_extract_gateway_info(request),
                request=_extract_request_info(request),
            )

            return VerifyResponse(valid=True, claims=claims)
        except Exception as e:
            await audit_service.log_event(
                "coupon_verify_failed",
                actor,
                "verify",
                "unknown",
                {"reason": str(e)},
                correlation_id=corr,
                gateway=_extract_gateway_info(request),
                request=_extract_request_info(request),
            )
            return VerifyResponse(valid=False, error=str(e))
        finally:
            COUPON_VERIFY_TOTAL.inc()


@router.post("/revoke", response_model=RevokeResponse)
async def revoke_token(
    req: RevokeRequest,
    request: Request,
    authorization: Optional[str] = Header(None),
    x_actor: Optional[str] = Header(None),
):
    with REVOKE_LATENCY_SECONDS.time():
        revoke_jti(req.jti, ttl_seconds=3600, reason=req.reason)

    COUPON_REVOKE_TOTAL.inc()
    LAST_REVOKE_TS.set(now_unix())

    corr = _correlation_id(request)
    actor = x_actor or _resolve_actor(authorization, fallback="admin")

    await audit_service.log_event(
        "coupon_revoked",
        actor,
        "revoke",
        req.jti,
        {"reason": req.reason},
        correlation_id=corr,
        gateway=_extract_gateway_info(request),
        request=_extract_request_info(request),
    )

    return RevokeResponse(status="revoked", revoked_at=datetime.now(timezone.utc).isoformat())


# --- Week 4: Audit UI + Traceability APIs ---


@router.get("/audit-logs")
async def get_audit_logs(limit: int = Query(200, ge=1, le=2000)):
    # Backwards-compatible: return a raw list
    items, _total = await audit_store.list(limit=limit, offset=0)
    return items


@router.get("/audit-events")
async def get_audit_events(
    limit: int = Query(200, ge=1, le=2000),
    offset: int = Query(0, ge=0),
    event_type: Optional[str] = None,
    actor: Optional[str] = None,
    action: Optional[str] = None,
    resource: Optional[str] = None,
    correlation_id: Optional[str] = None,
    source: Optional[str] = None,
    signature_valid: Optional[bool] = None,
    text: Optional[str] = None,
    time_from: Optional[str] = None,
    time_to: Optional[str] = None,
):
    items, total = await audit_store.list(
        limit=limit,
        offset=offset,
        event_type=event_type,
        actor=actor,
        action=action,
        resource=resource,
        correlation_id=correlation_id,
        source=source,
        signature_valid=signature_valid,
        text=text,
        time_from=time_from,
        time_to=time_to,
    )
    return {"items": items, "total": total, "offset": offset, "limit": limit}


@router.get("/kafka-events")
async def get_kafka_events(
    limit: int = Query(200, ge=1, le=2000),
    offset: int = Query(0, ge=0),
    event_type: Optional[str] = None,
    actor: Optional[str] = None,
    action: Optional[str] = None,
    resource: Optional[str] = None,
    correlation_id: Optional[str] = None,
    signature_valid: Optional[bool] = None,
    text: Optional[str] = None,
    time_from: Optional[str] = None,
    time_to: Optional[str] = None,
):
    items, total = await audit_store.list(
        limit=limit,
        offset=offset,
        event_type=event_type,
        actor=actor,
        action=action,
        resource=resource,
        correlation_id=correlation_id,
        source="kafka",
        signature_valid=signature_valid,
        text=text,
        time_from=time_from,
        time_to=time_to,
    )
    return {"items": items, "total": total, "offset": offset, "limit": limit}


@router.get("/trace/correlation/{correlation_id}")
async def trace_by_correlation(correlation_id: str):
    items = await audit_store.trace_by_correlation(correlation_id)
    return {"correlation_id": correlation_id, "items": items}


@router.get("/trace/resource/{resource}")
async def trace_by_resource(resource: str):
    items = await audit_store.trace_by_resource(resource)
    return {"resource": resource, "items": items}


@router.get("/audit-summary")
async def audit_summary():
    return await audit_store.summary()


@router.get("/consumer-status")
async def consumer_status():
    summary = await audit_store.summary()
    return summary.get("kafka", {})


@router.post("/log-event")
async def log_event(event: dict, request: Request):
    await audit_service.log_event(
        event.get("event_type", "manual"),
        event.get("actor", "unknown"),
        event.get("action", "log"),
        event.get("resource", "none"),
        event.get("details", {}),
        correlation_id=_correlation_id(request),
        gateway=_extract_gateway_info(request),
        request=_extract_request_info(request),
    )
    return {"status": "logged"}


@router.post("/filter-authorized")
async def filter_authorized_resources(req: PartialEvalRequest):
    # Placeholder for week3 partial evaluation endpoint (not wired in this MVP)
    return {"authorized": []}
