from datetime import datetime, timezone
from typing import Any, Dict, Optional, List
from jose import jwt # <--- YENİ EKLENDİ
from core.config import settings # <--- YENİ EKLENDİ

from fastapi import APIRouter, Header, HTTPException, Request, Query, Depends

from api.models import (
    CouponRequest,
    CouponResponse,
    VerifyRequest,
    VerifyResponse,
    RevokeRequest,
    RevokeResponse,
    DelegationRequest,
    PartialEvalRequest,
)

from core.security import create_coupon, verify_coupon, verify_oidc_token, get_mtls_identity, get_public_key_pem
from services.revocation import revoke_jti, is_jti_revoked
from services.delegation import add_delegation, get_delegations_for_resource
from services.audit import audit_service
from services.audit_store import audit_store
try:
    from services.audit_indexer import audit_indexer
except ImportError:
    audit_indexer = None

from core.metrics import (
    COUPON_ISSUE_TOTAL,
    ISSUE_LATENCY_SECONDS,
    OPA_DENY_TOTAL,
)
from core.policy import policy_engine
from slowapi import Limiter
from slowapi.util import get_remote_address
from core.limiter import limiter

router = APIRouter()

# ... (Helper fonksiyonlar aynı kalsın: _derive_correlation_id vb.) ...
def _derive_correlation_id(request: Request) -> str:
    return getattr(request.state, "correlation_id", "unknown")

def _extract_gateway_info(request: Request) -> Dict[str, Any]:
    return {
        "gateway_id": request.headers.get("x-gateway-id"),
        "forwarded_for": request.headers.get("x-forwarded-for"),
        "user_agent": request.headers.get("user-agent"),
    }

def _extract_request_info(request: Request) -> Dict[str, Any]:
    return {
        "method": request.method,
        "path": request.url.path,
        "client_ip": request.client.host if request.client else None,
    }

@router.get("/health", tags=["System"])
async def health():
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}


@router.get("/public-key", tags=["System"])
async def public_key():
    """Expose the CA public key for local verification.

    This enables SDK `offline_strategy="local"` by letting clients fetch and
    cache the key material.
    """
    return {"public_key_pem": get_public_key_pem(), "kid": "v4.public"}

@router.post("/issue", response_model=CouponResponse, tags=["Issuance"])
@limiter.limit("5/minute")
async def issue_coupon(request: Request, body: CouponRequest, authorization: str = Header(None)):
    """
    Issue a scoped, short-lived coupon.
    """
    # 1. Authentication (GÜNCELLENDİ: Hem HS256 hem RS256 destekler)
    identity = "anonymous"
    scopes = "none"

    if authorization:
        try:
            scheme, token = authorization.split()
            if scheme.lower() == "bearer":
                # ÖNCE: Backend'in kendi Secret Key'i ile (HS256) çözmeyi dene (Senin Token)
                try:
                    claims = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
                except Exception:
                    # OLMADIYSA: OIDC (RS256) doğrulaması yap (Gerçek Senaryo)
                    claims = verify_oidc_token(token)
                
                identity = claims.get("sub", "unknown")
                scopes = claims.get("scope", "none")
        except Exception as e:
            # Token geçersizse anonim kalır
            print(f"Auth failed: {e}")
            pass
    
    # Check mTLS if OIDC not present
    if identity == "anonymous":
        mtls_id = get_mtls_identity(request)
        if mtls_id:
            identity = mtls_id

    # 2. Authorization (Policy Check via OPA)
    # Burada token içindeki "aud" yerine kullanıcının "sub" (kimliği) önemli.
    policy_input = {
        "path": "/issue",     # OPA kuralı için path ekledik
        "method": "POST",     # OPA kuralı için method ekledik
        "token": {"sub": identity, "aud": "disc", "scope": scopes}, 
        "audience": body.audience,
        "scope": body.scope,
        "resource": body.resource,
        "delegations": {} 
    }
    
    if body.resource:
        policy_input["delegations"] = {
            body.resource: get_delegations_for_resource(body.resource)
        }

    allowed = policy_engine.check_permission(policy_input)
    
    if not allowed:
        OPA_DENY_TOTAL.inc()
        await audit_service.log_event(
            event_type="coupon_denied",
            actor=identity,
            action="issue",
            resource=body.resource or "n/a",
            details={"reason": "Policy denied", "scope": body.scope},
            correlation_id=_derive_correlation_id(request),
            gateway=_extract_gateway_info(request),
            request=_extract_request_info(request)
        )
        raise HTTPException(status_code=403, detail="Policy denied by OPA")

    # 3. Mint Coupon
    try:
        with ISSUE_LATENCY_SECONDS.time():
            coupon = create_coupon(
                subject=identity,
                audience=body.audience,
                scope=body.scope,
                ttl_seconds=body.ttl_seconds
            )
        
        COUPON_ISSUE_TOTAL.inc()

        await audit_service.log_event(
            event_type="coupon_issued",
            actor=identity,
            action="issue",
            resource=body.resource or "n/a",
            details={"audience": body.audience, "scope": body.scope, "ttl": body.ttl_seconds},
            correlation_id=_derive_correlation_id(request),
            gateway=_extract_gateway_info(request),
            request=_extract_request_info(request)
        )
        
        # Extract JTI (useful for revoke flows & debugging)
        jti = None
        try:
            jti = verify_coupon(coupon).get("jti")
        except Exception:
            jti = None

        return {"coupon": coupon, "expires_in": body.ttl_seconds, "jti": jti}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ... (Kalan fonksiyonlar aynı: verify, revoke, audit/search vb.) ...
# verify, revoke, audit_summary_endpoint, consumer_status_endpoint, search_audit_logs_endpoint 
# fonksiyonlarını silmediğinden emin ol, dosyanın alt tarafı aynı kalsın.
@router.post("/verify", response_model=VerifyResponse, tags=["Verification"])
async def verify(body: VerifyRequest, request: Request):
    try:
        claims = verify_coupon(body.coupon)
        jti = claims.get("jti")
        if jti and is_jti_revoked(jti):
            raise ValueError("Token is revoked")
        return {"valid": True, "claims": claims}
    except Exception as e:
        return {"valid": False, "error": str(e)}

@router.post("/revoke", response_model=RevokeResponse, tags=["Revocation"])
async def revoke(body: RevokeRequest, request: Request, authorization: str = Header(None)):
    revoke_jti(body.jti, ttl_seconds=3600, reason=body.reason)
    await audit_service.log_event(
        event_type="coupon_revoked",
        actor="admin",
        action="revoke",
        resource=body.jti,
        details={"reason": body.reason},
        correlation_id=_derive_correlation_id(request),
        gateway=_extract_gateway_info(request),
        request=_extract_request_info(request)
    )
    return {"status": "revoked", "revoked_at": datetime.now(timezone.utc).isoformat()}

@router.get("/audit-summary")
async def audit_summary_endpoint():
    return await audit_store.summary()

@router.get("/consumer-status")
async def consumer_status_endpoint():
    summary = await audit_store.summary()
    return summary.get("kafka", {})

@router.get("/audit/search", tags=["Audit"])
async def search_audit_logs_endpoint(
    request: Request,
    actor: str = Query(None),
    action: str = Query(None),
    limit: int = 50,
    authorization: str = Header(None)
):
    # Basit authentication
    identity = "anonymous"
    scopes = "none"
    if authorization:
        try:
            scheme, token = authorization.split()
            if scheme.lower() == "bearer":
                try:
                     # Önce HS256 dene
                     claims = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
                except:
                     # Sonra OIDC dene
                     claims = verify_oidc_token(token)
                identity = claims.get("sub", "anonymous")
                scopes = claims.get("scope", "none")
        except:
            pass

    policy_input = {
        "path": "/audit/search",
        "method": "GET",
        "token": {"sub": identity, "aud": "disc", "scope": scopes}
    }

    allowed = policy_engine.check_permission(policy_input)
    if not allowed:
        raise HTTPException(status_code=403, detail="Admin access required")

    if audit_indexer:
        return await audit_indexer.search_audit_logs(actor=actor, action=action, limit=limit)
    return []

@router.post("/delegation", tags=["Policy"])
async def create_delegation(body: DelegationRequest):
    add_delegation("me", body.delegate, body.resource, body.ttl)
    return {"status": "delegated"}

@router.post("/policy/partial-eval", tags=["Policy"])
async def partial_eval(body: PartialEvalRequest):
    return {"result": {"allow": True, "conditions": ["always_true"]}}