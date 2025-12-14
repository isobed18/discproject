from fastapi import APIRouter, HTTPException, Depends, Header, Request
from typing import Optional
from datetime import datetime, timezone
from .models import CouponRequest, CouponResponse, VerifyRequest, VerifyResponse, RevokeRequest, RevokeResponse, DelegationRequest, PartialEvalRequest
from ..core.security import create_coupon, verify_coupon, verify_oidc_token, get_mtls_identity
from ..services.revocation import revoke_jti, is_jti_revoked
from ..services.delegation import add_delegation, get_delegations_for_resource
from ..core.metrics import (
    COUPON_ISSUE_TOTAL, COUPON_VERIFY_TOTAL, COUPON_REVOKE_TOTAL,
    ISSUE_LATENCY_SECONDS, VERIFY_LATENCY_SECONDS, REVOKE_LATENCY_SECONDS,
    LAST_REVOKE_TS, now_unix,
    OPA_DENY_TOTAL, OPA_UNAVAILABLE_TOTAL
)

router = APIRouter()

@router.post("/delegations")
def create_delegation(req: DelegationRequest):
    # In a real app, we would verify that the caller OWNS the resource.
    # For MVP, we allow anyone to create a delegation.
    add_delegation("owner", req.delegate, req.resource, req.ttl)
    return {"status": "delegation_created", "delegate": req.delegate, "resource": req.resource}

@router.post("/filter-authorized")
def filter_authorized_resources(
    req: PartialEvalRequest,
    request: Request,
    authorization: Optional[str] = Header(None)
):
    """
    Demonstrates Partial Evaluation (or Batch Check).
    Takes a list of resources and returns only those that are allowed.
    """
    from ..core.policy import policy_engine
    
    # 1. Identify the user (Extract from Token or default to anonymous)
    user_id = "anonymous"
    if authorization:
        try:
            scheme, token = authorization.split()
            if scheme.lower() == "bearer":
                claims = verify_oidc_token(token)
                user_id = claims.get("sub", "unknown")
        except Exception:
            pass 

    allowed_resources = []
    
    # In a real OPA Partial Eval, we would send the policy + unknown input 
    # and get back the conditions. 
    # For MVP, we iterate (Batch Check) which is a common specific case of Partial Eval usage.
    
    for res in req.resources:
        # Mocking the input context. In reality this depends on WHO is asking.
        # We assume "anonymous" or "test-user" for this open endpoint unless auth header is parsed.
        # For simplicity, we just check against the hardcoded policy logic or OPA.
        
        # We'll use the check_permission method.
        # Note: "token" part mocks the requester having a token for this resource
        # purely to see if the POLICY (delegation/admin) would allow it.
        
        input_data = {
            "resource": res,
            "audience": req.audience,
            "scope": req.action,
            "token": {"sub": user_id, "aud": req.audience, "scope": "default"}, # Use real user_id
            "delegations": {res: get_delegations_for_resource(res)}
        }
        
        if policy_engine.check_permission(input_data):
            allowed_resources.append(res)
            
    return {"authorized": allowed_resources}

@router.post("/issue", response_model=CouponResponse)
def issue_coupon(
    req: CouponRequest, 
    request: Request,
    authorization: Optional[str] = Header(None)
):
    # ⏱️ LATENCY ÖLÇÜMÜ BAŞLIYOR
    with ISSUE_LATENCY_SECONDS.time():

        # 1. OIDC Authentication
        user_id = "anonymous"
        if authorization:
            try:
                scheme, token = authorization.split()
                if scheme.lower() == "bearer":
                    claims = verify_oidc_token(token)
                    user_id = claims.get("sub", "unknown")
            except Exception:
                pass  # MVP / DEV_MODE için fail-open

        # 2. mTLS Identity
        mtls_id = get_mtls_identity(request.headers)

        # 3. POLICY CHECK (OPA)
        from ..core.policy import policy_engine

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
            # 🚨 OPA UNAVAILABLE (fail-closed path)
            OPA_UNAVAILABLE_TOTAL.inc()
            raise HTTPException(
                status_code=503,
                detail="OPA unavailable"
            )

        if not allowed:
            # 🚫 OPA DENY
            OPA_DENY_TOTAL.inc()
            raise HTTPException(
                status_code=403,
                detail="Policy denied by OPA"
            )

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

        # 5. AUDIT LOG
        audit_logs.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": "coupon_issued",
            "actor": user_id,
            "action": "issue",
            "resource": jti,
            "details": {
                "audience": req.audience,
                "scope": req.scope
            }
        })

        # ✅ SUCCESS COUNTER
        COUPON_ISSUE_TOTAL.inc()

        return CouponResponse(
            coupon=token,
            expires_in=req.ttl_seconds or 300,
            jti=jti
        )

@router.post("/verify", response_model=VerifyResponse)
def verify_token(req: VerifyRequest):
    with VERIFY_LATENCY_SECONDS.time():
        try:
            claims = verify_coupon(req.coupon)

            # Check revocation
            jti = claims.get("jti")
            if jti and is_jti_revoked(jti):
                return VerifyResponse(valid=False, error="revoked")

            return VerifyResponse(valid=True, claims=claims)

        except Exception as e:
            return VerifyResponse(valid=False, error=str(e))
        finally:
            # ✅ Always count verify attempts
            COUPON_VERIFY_TOTAL.inc()


@router.post("/revoke", response_model=RevokeResponse)
def revoke_token(req: RevokeRequest):
    with REVOKE_LATENCY_SECONDS.time():
        revoke_jti(
            req.jti,
            ttl_seconds=3600,
            reason=req.reason
        )

    # ✅ Metrics
    COUPON_REVOKE_TOTAL.inc()
    LAST_REVOKE_TS.set(now_unix())

    return RevokeResponse(
        status="revoked",
        revoked_at=datetime.now(timezone.utc).isoformat()
    )


# Mock in-memory audit log for MVP
audit_logs = []

@router.get("/audit-logs")
def get_audit_logs():
    return audit_logs

@router.post("/log-event")
def log_event(event: dict):
    # Internal endpoint to log events (in real app, this happens automatically)
    audit_logs.append(event)
    return {"status": "logged"}
