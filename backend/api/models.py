from pydantic import BaseModel
from typing import Optional, Dict, Any

class CouponRequest(BaseModel):
    audience: str
    scope: str
    resource: Optional[str] = None # The resource being accessed (for delegation checks)
    ttl_seconds: Optional[int] = 300
    # In a real mTLS scenario, we might not need to pass cnf explicitly if we extract it from the cert
    # But for MVP/testing, we might allow passing it or infer it.

class DelegationRequest(BaseModel):
    delegate: str
    resource: str
    ttl: int = 3600

class PartialEvalRequest(BaseModel):
    resources: list[str]
    action: str = "read"
    audience: str = "default"
    
class CouponResponse(BaseModel):
    coupon: str
    expires_in: int
    jti: Optional[str] = None

class VerifyRequest(BaseModel):
    coupon: str

class VerifyResponse(BaseModel):
    valid: bool
    claims: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class RevokeRequest(BaseModel):
    jti: str
    reason: Optional[str] = "unspecified"

class RevokeResponse(BaseModel):
    status: str
    revoked_at: str
