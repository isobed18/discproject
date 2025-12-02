from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone
from .models import CouponRequest, CouponResponse, VerifyRequest, VerifyResponse, RevokeRequest, RevokeResponse
from ..core.security import create_coupon, verify_coupon
from ..services.revocation import revoke_jti, is_jti_revoked

router = APIRouter()

@router.post("/issue", response_model=CouponResponse)
def issue_coupon(req: CouponRequest):
    # TODO: Validate client identity (mTLS/OIDC) and check policies (OPA)
    # For MVP, we assume the request is authorized if it reaches here (or we add a dummy check)
    
    # Create the coupon
    token = create_coupon(
        subject="test-user", # In real app, get from auth context
        audience=req.audience,
        scope=req.scope,
        ttl_seconds=req.ttl_seconds or 300
    )
    
    # We need to extract JTI to return it, or we can decode the token we just made
    # For efficiency, create_coupon could return it, but for now let's decode
    decoded = verify_coupon(token)
    
    return CouponResponse(
        coupon=token,
        expires_in=req.ttl_seconds or 300,
        jti=decoded.get("jti") # pyseto might not set jti by default if we didn't pass it? check implementation
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
    # TODO: Check admin permissions
    
    # We need to know the TTL to set in Redis. 
    # Ideally, the caller provides it or we look it up. 
    # For MVP, we'll set a default safe TTL (e.g., 1 hour) or require it in request.
    # Let's assume 1 hour for now if not known.
    revoke_jti(req.jti, ttl_seconds=3600, reason=req.reason)
    
    return RevokeResponse(
        status="revoked",
        revoked_at=datetime.now(timezone.utc).isoformat()
    )
