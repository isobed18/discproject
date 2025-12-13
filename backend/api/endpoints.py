from fastapi import APIRouter, HTTPException, Depends, Header, Request
from typing import Optional
from datetime import datetime, timezone
from .models import CouponRequest, CouponResponse, VerifyRequest, VerifyResponse, RevokeRequest, RevokeResponse
from ..core.security import create_coupon, verify_coupon, verify_oidc_token, get_mtls_identity
from ..services.revocation import revoke_jti, is_jti_revoked

router = APIRouter()

@router.post("/issue", response_model=CouponResponse)
def issue_coupon(
    req: CouponRequest, 
    request: Request,
    authorization: Optional[str] = Header(None)
):
    # 1. OIDC Authentication
    user_id = "anonymous"
    if authorization:
        try:
            scheme, token = authorization.split()
            if scheme.lower() == "bearer":
                claims = verify_oidc_token(token)
                user_id = claims.get("sub", "unknown")
        except Exception:
            pass # Fail open for MVP if no token, or enforce? 
            # Let's enforce if it looks like a token was attempted but failed.
            # For MVP simplicity, if no token, we default to "test-user" or "anonymous"
            # unless we want to strictly enforce it.
            
    # 2. mTLS Identity
    mtls_id = get_mtls_identity(request.headers)
    
    # Policy Check (OPA)
    from ..core.policy import policy_engine
    
    # Construct the input for OPA
    # ideally we pass the full token claims, but for now we pass what we have
    # We haven't created the token yet, but we know what will be in it.
    # Typically OPA checks happen *before* issuance based on the requester's identity (OIDC/mTLS)
    # AND the requested parameters (scope, audience).
    
    policy_input = {
        "audience": req.audience,
        "scope": req.scope,
        "token": {
            "sub": user_id,
            "aud": req.audience, # The audience of the token we ARE ABOUT TO MINT
            "scope": req.scope # The scope we ARE ABOUT TO MINT
        },
        # For delegation mockup:
        "delegations": {
            # Mock delegation: "resource-123" can be accessed by "user_a" (or whoever the user_id is)
            # In a real app, you'd fetch this from DB
            "resource-123": ["test-user", "anonymous"] 
        },
        "resource": "resource-123" # Mock resource for checking delegation
    }
    
    allowed = policy_engine.check_permission(policy_input)
    if not allowed:
        raise HTTPException(status_code=403, detail="Policy denied by OPA")

    # Create the coupon
    cnf = {"x5t#S256": mtls_id.split(":")[1]} if mtls_id else None
    
    token = create_coupon(
        subject=user_id, 
        audience=req.audience,
        scope=req.scope,
        ttl_seconds=req.ttl_seconds or 300,
        cnf=cnf
    )
    
    # We need to extract JTI to return it, or we can decode the token we just made
    decoded = verify_coupon(token)
    jti = decoded.get("jti")

    # Log event
    audit_logs.append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_type": "coupon_issued",
        "actor": "test-user",
        "action": "issue",
        "resource": jti,
        "details": {"audience": req.audience, "scope": req.scope}
    })
    
    return CouponResponse(
        coupon=token,
        expires_in=req.ttl_seconds or 300,
        jti=jti
    )

@router.post("/verify", response_model=VerifyResponse)
def verify_token(req: VerifyRequest):
    try:
        claims = verify_coupon(req.coupon)
        
        # Check revocation
        jti = claims.get("jti")
        if jti and is_jti_revoked(jti):
            return VerifyResponse(valid=False, error="revoked")
            
        return VerifyResponse(valid=True, claims=claims)
    except Exception as e:
        return VerifyResponse(valid=False, error=str(e))

@router.post("/revoke", response_model=RevokeResponse)
def revoke_token(req: RevokeRequest):
    # ... (existing code)
    revoke_jti(req.jti, ttl_seconds=3600, reason=req.reason)
    
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
