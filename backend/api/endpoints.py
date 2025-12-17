from fastapi import APIRouter, HTTPException, Depends, Header, Request
from typing import Optional
from datetime import datetime, timezone

# --- DÜZELTME: NOKTALARI SİLDİK (Absolute Import) ---
# Kendi klasöründeki (api) modeller için nokta kalabilir veya api.models diyebilirsin
from .models import CouponRequest, CouponResponse, VerifyRequest, VerifyResponse, RevokeRequest, RevokeResponse, DelegationRequest, PartialEvalRequest

# Ama diğer klasörler için direkt isimlerini kullanıyoruz:
from core.security import create_coupon, verify_coupon, verify_oidc_token, get_mtls_identity
from services.revocation import revoke_jti, is_jti_revoked
from services.delegation import add_delegation, get_delegations_for_resource
from services.audit import audit_service
from core.metrics import (
    COUPON_ISSUE_TOTAL, COUPON_VERIFY_TOTAL, COUPON_REVOKE_TOTAL,
    ISSUE_LATENCY_SECONDS, VERIFY_LATENCY_SECONDS, REVOKE_LATENCY_SECONDS,
    LAST_REVOKE_TS, now_unix,
    OPA_DENY_TOTAL, OPA_UNAVAILABLE_TOTAL
)
from core.policy import policy_engine

router = APIRouter()

@router.post("/delegations")
async def create_delegation(req: DelegationRequest):
    # Week 3: Delegation Creation
    add_delegation("owner", req.delegate, req.resource, req.ttl)
    return {"status": "delegation_created", "delegate": req.delegate, "resource": req.resource}

@router.post("/issue", response_model=CouponResponse)
async def issue_coupon(
    req: CouponRequest, 
    request: Request,
    authorization: Optional[str] = Header(None)
):
    with ISSUE_LATENCY_SECONDS.time():
        # 1. User Identity
        user_id = "anonymous"
        if authorization:
            try:
                scheme, token = authorization.split()
                if scheme.lower() == "bearer":
                    claims = verify_oidc_token(token)
                    user_id = claims.get("sub", "unknown")
            except Exception:
                pass

        # 2. mTLS Identity
        mtls_id = get_mtls_identity(request.headers)

        # 3. POLICY CHECK (Week 3 - OPA)
        delegated_users = []
        if req.resource:
            delegated_users = get_delegations_for_resource(req.resource)

        policy_input = {
            "audience": req.audience,
            "scope": req.scope,
            "token": {
                "sub": user_id,
                "aud": req.audience,
                "scope": req.scope
            },
            "delegations": {
                req.resource if req.resource else "global": delegated_users
            },
            "resource": req.resource
        }

        try:
            allowed = policy_engine.check_permission(policy_input)
        except Exception:
            OPA_UNAVAILABLE_TOTAL.inc()
            raise HTTPException(status_code=503, detail="OPA unavailable")

        if not allowed:
            OPA_DENY_TOTAL.inc()
            raise HTTPException(status_code=403, detail="Policy denied by OPA")

        # 4. CREATE COUPON
        cnf = {"x5t#S256": mtls_id.split(":")[1]} if mtls_id else None
        token = create_coupon(
            subject=user_id, 
            audience=req.audience,
            scope=req.scope,
            ttl_seconds=req.ttl_seconds or 300,
            cnf=cnf
        )

        decoded = verify_coupon(token)
        jti = decoded.get("jti")

        # 5. AUDIT LOG (Week 4 - Kafka)
        await audit_service.log_event(
            event_type="coupon_issued",
            actor=user_id,
            action="issue",
            resource=jti,
            details={"audience": req.audience, "scope": req.scope}
        )

        COUPON_ISSUE_TOTAL.inc()
        return CouponResponse(coupon=token, expires_in=req.ttl_seconds or 300, jti=jti)

# --- Diğer endpointler ---
@router.post("/verify", response_model=VerifyResponse)
async def verify_token(req: VerifyRequest):
    with VERIFY_LATENCY_SECONDS.time():
        try:
            claims = verify_coupon(req.coupon)
            jti = claims.get("jti")
            if jti and is_jti_revoked(jti):
                await audit_service.log_event("coupon_verify_failed", "unknown", "verify", jti, {"reason": "revoked"})
                return VerifyResponse(valid=False, error="revoked")
            return VerifyResponse(valid=True, claims=claims)
        except Exception as e:
            return VerifyResponse(valid=False, error=str(e))
        finally:
            COUPON_VERIFY_TOTAL.inc()

@router.post("/revoke", response_model=RevokeResponse)
async def revoke_token(req: RevokeRequest):
    with REVOKE_LATENCY_SECONDS.time():
        revoke_jti(req.jti, ttl_seconds=3600, reason=req.reason)
    COUPON_REVOKE_TOTAL.inc()
    LAST_REVOKE_TS.set(now_unix())
    await audit_service.log_event("coupon_revoked", "admin", "revoke", req.jti, {"reason": req.reason})
    return RevokeResponse(status="revoked", revoked_at=datetime.now(timezone.utc).isoformat())

@router.get("/audit-logs")
async def get_audit_logs():
    return {"message": "Audit logs are in Kafka (topic: audit-logs)."}

@router.post("/log-event")
async def log_event(event: dict):
    await audit_service.log_event(
        event.get("event_type", "manual"), event.get("actor", "unknown"),
        event.get("action", "log"), event.get("resource", "none"), event.get("details", {})
    )
    return {"status": "logged"}

@router.post("/filter-authorized")
async def filter_authorized_resources(req: PartialEvalRequest):
    return {"authorized": []}