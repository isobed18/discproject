from pydantic import BaseModel
from typing import Optional, Dict, Any, List

class CouponRequest(BaseModel):
    audience: str
    scope: str
    resource: Optional[str] = None
    ttl_seconds: Optional[int] = 300

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
