from fastapi import APIRouter, HTTPException, Depends, Header, Request
from typing import Optional, List
from datetime import datetime, timezone

from .models import (
    CouponRequest, CouponResponse, VerifyRequest, VerifyResponse, 
    RevokeRequest, RevokeResponse, DelegationRequest, PartialEvalRequest
)
from ..core.security import create_coupon, verify_coupon, verify_oidc_token, get_mtls_identity
from ..services.revocation import revoke_jti, is_jti_revoked
from ..services.delegation import add_delegation, get_delegations_for_resource
from ..core.policy import policy_engine
# NEW: Import Audit Service
from ..services.audit import audit_logger, audit_logs

router = APIRouter()

# --- Week 4: Audit Log Viewer Endpoint ---
@router.get("/audit-logs")
async def get_audit_logs():
    """Returns the latest logs consumed from Kafka."""
    return audit_logs

# --- Week 3: Delegation Endpoint ---
@router.post("/delegations")
async def create_delegation(req: DelegationRequest): # Changed to async
    add_delegation("owner", req.delegate, req.resource, req.ttl)
    
    # NEW: Log to Kafka
    await audit_logger.log_event(
        event_type="delegation",
        actor="owner",
        action="grant",
        resource=req.resource,
        details={"delegate": req.delegate, "ttl": req.ttl}
    )
    
    return {
        "status": "delegation_created", 
        "delegate": req.delegate, 
        "resource": req.resource
    }

# --- Week 3: Coupon Issuance with Policy Check ---
@router.post("/issue", response_model=CouponResponse)
async def issue_coupon( # Changed to async
    req: CouponRequest, 
    request: Request,
    authorization: Optional[str] = Header(None)
):
    # 1. Authentication & Scope Extraction
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
            
    # 2. mTLS Identity
    mtls_id = get_mtls_identity(request.headers)
    
    # 3. Retrieve Active Delegations
    delegated_users = []
    if req.resource:
        delegated_users = get_delegations_for_resource(req.resource)
    
    # 4. Prepare Input for OPA
    policy_input = {
        "audience": req.audience,
        "scope": req.scope,          
        "resource": req.resource,    
        "token": {
            "sub": user_id,
            "aud": req.audience, 
            "scope": user_scope      
        },
        "delegations": {
            req.resource if req.resource else "global": delegated_users 
        }
    }
    
    # 5. Policy Enforcement Point (PEP)
    allowed = policy_engine.check_permission(policy_input)
    
    if not allowed:
        # NEW: Log Failed Attempt
        await audit_logger.log_event(
            event_type="access_denied",
            actor=user_id,
            action="issue_coupon",
            resource=req.resource or "unknown",
            details={"reason": "Policy denied by OPA"}
        )
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
    
    decoded = verify_coupon(token)
    
    
    await audit_logger.log_event(
        event_type="issue_coupon",
        actor=user_id,
        action="issue",
        resource=decoded.get("jti"), # Log JTI as resource
        details={"audience": req.audience, "scope": req.scope}
    )
    
    return CouponResponse(
        coupon=token,
        expires_in=req.ttl_seconds or 300,
        jti=decoded.get("jti")
    )

@router.post("/verify", response_model=VerifyResponse)
async def verify_token(req: VerifyRequest): # Changed to async
    try:
        claims = verify_coupon(req.coupon)
        jti = claims.get("jti")
        if jti and is_jti_revoked(jti):
            return VerifyResponse(valid=False, error="revoked")
        return VerifyResponse(valid=True, claims=claims)
    except Exception as e:
        return VerifyResponse(valid=False, error=str(e))

@router.post("/revoke", response_model=RevokeResponse)
async def revoke_token(req: RevokeRequest): # Changed to async
    revoke_jti(req.jti, ttl_seconds=3600, reason=req.reason)
    
    # NEW: Log Revocation
    await audit_logger.log_event(
        event_type="revocation",
        actor="admin", # Assuming admin endpoint
        action="revoke",
        resource=req.jti,
        details={"reason": req.reason}
    )
    
    return RevokeResponse(
        status="revoked",
        revoked_at=datetime.now(timezone.utc).isoformat()
    )

@router.post("/filter-authorized")
async def filter_authorized_resources( # Changed to async
    req: PartialEvalRequest,
    request: Request,
    authorization: Optional[str] = Header(None)
):

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

    allowed_resources = []
    for res in req.resources:
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
        if policy_engine.check_permission(policy_input):
            allowed_resources.append(res)
            
    return allowed_resources