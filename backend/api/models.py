from pydantic import BaseModel
from typing import Optional, List, Dict, Any

# --- Coupon Models ---
class CouponRequest(BaseModel):
    audience: str
    scope: str
    resource: Optional[str] = None # Resource being accessed (crucial for delegation checks)
    ttl_seconds: Optional[int] = 300

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

# --- Week 3: Delegation & Policy Models ---

class DelegationRequest(BaseModel):
    delegate: str   # The user receiving permission (e.g., "user:123")
    resource: str   # The target resource (e.g., "doc:secure-1")
    ttl: int = 3600 # Duration of delegation in seconds

class PartialEvalRequest(BaseModel):
    """
    Used for batch filtering authorized resources.
    """
    resources: List[str]
    action: str = "read"
    audience: str = "default"