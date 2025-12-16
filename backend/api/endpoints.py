from fastapi import APIRouter, HTTPException, Depends, Header, Request
from typing import Optional
from datetime import datetime, timezone

from .models import (
    CouponRequest, CouponResponse, VerifyRequest, VerifyResponse, 
    RevokeRequest, RevokeResponse, DelegationRequest, PartialEvalRequest
)
from ..core.security import create_coupon, verify_coupon, verify_oidc_token, get_mtls_identity
from ..services.revocation import revoke_jti, is_jti_revoked
from ..services.delegation import add_delegation, get_delegations_for_resource
from ..core.policy import policy_engine

router = APIRouter()

# --- Week 3: Delegation Endpoint ---
@router.post("/delegations")
def create_delegation(req: DelegationRequest):
    """
    Creates a new delegation entry in Redis.
    Allows 'req.delegate' to access 'req.resource'.
    """
    # In a real system, we would verify that the caller OWNS the resource first.
    add_delegation("owner", req.delegate, req.resource, req.ttl)
    return {
        "status": "delegation_created", 
        "delegate": req.delegate, 
        "resource": req.resource
    }

# --- Week 3: Coupon Issuance with Policy Check ---
@router.post("/issue", response_model=CouponResponse)
def issue_coupon(
    req: CouponRequest, 
    request: Request,
    authorization: Optional[str] = Header(None)
):
    # 1. Authentication & Scope Extraction
    user_id = "anonymous"
    user_scope = [] # Scope coming from OIDC token
    
    if authorization:
        try:
            scheme, token = authorization.split()
            if scheme.lower() == "bearer":
                claims = verify_oidc_token(token)
                user_id = claims.get("sub", "unknown")
                # Extract scope from token (handle both string and list formats)
                raw_scope = claims.get("scope", "")
                if isinstance(raw_scope, str):
                    user_scope = raw_scope.split(" ")
                elif isinstance(raw_scope, list):
                    user_scope = raw_scope
        except Exception:
            pass # Continue as anonymous or fail depending on strictness
            
    # 2. mTLS Identity
    mtls_id = get_mtls_identity(request.headers)
    
    # 3. Retrieve Active Delegations
    delegated_users = []
    if req.resource:
        delegated_users = get_delegations_for_resource(req.resource)
    
    # 4. Prepare Input for OPA
    policy_input = {
        "audience": req.audience,
        "scope": req.scope,          # The scope REQUESTED
        "resource": req.resource,    # The resource REQUESTED
        "token": {
            "sub": user_id,
            "aud": req.audience, 
            "scope": user_scope      # The scope POSSESSED by the user
        },
        "delegations": {
            # Pass delegation list for the requested resource
            req.resource if req.resource else "global": delegated_users 
        }
    }
    
    # 5. Policy Enforcement Point (PEP)
    allowed = policy_engine.check_permission(policy_input)
    if not allowed:
        raise HTTPException(status_code=403, detail="Policy denied by OPA")

    # 6. Mint Coupon
    cnf = {"x5t#S256": mtls_id.split(":")[1]} if mtls_id else None
    
    token = create_coupon(
        subject=user_id, 
        audience=req.audience,
        scope=req.scope,
        ttl_seconds=req.ttl_seconds or 300,
        cnf=cnf
    )
    
    # Verify immediately to get JTI for response
    decoded = verify_coupon(token)
    
    return CouponResponse(
        coupon=token,
        expires_in=req.ttl_seconds or 300,
        jti=decoded.get("jti")
    )

# --- Standard Verification & Revocation ---
@router.post("/verify", response_model=VerifyResponse)
def verify_token(req: VerifyRequest):
    try:
        claims = verify_coupon(req.coupon)
        
        # Check Redis for revocation
        jti = claims.get("jti")
        if jti and is_jti_revoked(jti):
            return VerifyResponse(valid=False, error="revoked")
            
        return VerifyResponse(valid=True, claims=claims)
    except Exception as e:
        return VerifyResponse(valid=False, error=str(e))

@router.post("/revoke", response_model=RevokeResponse)
def revoke_token(req: RevokeRequest):
    revoke_jti(req.jti, ttl_seconds=3600, reason=req.reason)
    return RevokeResponse(
        status="revoked",
        revoked_at=datetime.now(timezone.utc).isoformat()
    )
@router.post("/filter-authorized")
def filter_authorized_resources(
    req: PartialEvalRequest,
    request: Request,
    authorization: Optional[str] = Header(None)
):
    """
    Week 3: Partial Evaluation (Toplu Yetki Kontrolü)
    Birden fazla kaynak için yetki sorulduğunda, sadece izin verilenleri döner.
    """
    # 1. Kimlik Bilgilerini Al
    user_id = "anonymous"
    user_scope = []
    
    if authorization:
        try:
            scheme, token = authorization.split()
            if scheme.lower() == "bearer":
                claims = verify_oidc_token(token)
                user_id = claims.get("sub", "unknown")
                raw_scope = claims.get("scope", "")
                if isinstance(raw_scope, str):
                    user_scope = raw_scope.split(" ")
                elif isinstance(raw_scope, list):
                    user_scope = raw_scope
        except Exception:
            pass

    # 2. Döngü ile Her Kaynağı Kontrol Et
    allowed_resources = []
    for res in req.resources:
        # Bu kaynak için delegasyon var mı?
        delegated_users = get_delegations_for_resource(res)
        
        policy_input = {
            "audience": req.audience,
            "scope": req.action,
            "resource": res,
            "token": {
                "sub": user_id,
                "aud": req.audience, 
                "scope": user_scope
            },
            "delegations": {
                res: delegated_users
            }
        }
        
        # OPA'ya sor
        if policy_engine.check_permission(policy_input):
            allowed_resources.append(res)
            
    return allowed_resources