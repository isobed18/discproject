from typing import List, Optional
from fastapi import APIRouter, Depends, Header, HTTPException, Query
from core.security import verify_oidc_token
from services.audit_indexer import audit_indexer
from core.policy import policy_engine

router = APIRouter()

@router.get("/audit/search", summary="Search Audit Logs")
async def search_audit_logs(
    actor: Optional[str] = Query(None, description="Filter by actor"),
    action: Optional[str] = Query(None, description="Filter by action"),
    limit: int = Query(50, le=100),
    authorization: Optional[str] = Header(None)
):
    """
    Search audit logs using Redis Indexer.
    Requires 'admin' role (Mocked via OPA or Token Scope for MVP).
    """
    # 1. Authentication (Who is asking?)
    user_id = "anonymous"
    roles = []
    if authorization:
        try:
            scheme, token = authorization.split()
            if scheme.lower() == "bearer":
                claims = verify_oidc_token(token)
                user_id = claims.get("sub", "unknown")
                # For MVP, we might assume roles are in the token or looked up.
                # Let's say claims has "roles" or we fetch from a user store.
                # mocking "admin" if subject is 'admin' or 'test-admin'
                if user_id in ["admin", "test-admin"] or "admin" in claims.get("roles", []):
                    roles.append("admin")
        except Exception:
            pass

    # 2. Authorization (RBAC via OPA)
    # We ask OPA: Can 'user_id' with 'roles' perform 'search' on 'audit'?
    policy_input = {
        "input": {
            "user": user_id,
            "roles": roles, # ["admin"] if verified
            "action": "search",
            "resource": "audit-logs"
        }
    }
    
    # For Week 4, we enforce Admin Only.
    # If using OPA, we need a policy for this. 
    # OR for MVP simplicity, we can just check code-side if not using Full OPA for system Ops.
    # Let's check code-side for now to ensure safety before OPA policy update.
    if "admin" not in roles:
        # Check OPA just in case we added a policy later
        # allowed = policy_engine.check_custom_policy("audit/search", policy_input)
        # if not allowed:
        raise HTTPException(status_code=403, detail="Admin access required")

    # 3. Search
    results = await audit_indexer.search(actor=actor, action=action, limit=limit)
    return {"results": results}
