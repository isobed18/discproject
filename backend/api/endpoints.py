from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone
from .models import CouponRequest, CouponResponse, VerifyRequest, VerifyResponse, RevokeRequest, RevokeResponse
from ..core.security import create_coupon, verify_coupon
from ..services.revocation import revoke_jti, is_jti_revoked

router = APIRouter()

@router.post("/issue", response_model=CouponResponse)
def issue_coupon(req: CouponRequest):
    # Policy Check (Simulating OPA)
    # Deny if scope contains "admin" unless audience is "internal-admin"
    if "admin" in req.scope and req.audience != "internal-admin":
        raise HTTPException(status_code=403, detail="Policy denied: 'admin' scope requires 'internal-admin' audience")

    # Create the coupon
    token = create_coupon(
        subject="test-user", # In real app, get from auth context
        audience=req.audience,
        scope=req.scope,
        ttl_seconds=req.ttl_seconds or 300
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
