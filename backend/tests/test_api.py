from fastapi.testclient import TestClient
from backend.main import app
from backend.core.security import verify_coupon

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_issue_coupon():
    response = client.post(
        "/v1/issue",
        json={"audience": "test-service", "scope": "read:data", "ttl_seconds": 60}
    )
    assert response.status_code == 200
    data = response.json()
    assert "coupon" in data
    assert "jti" in data
    assert data["expires_in"] == 60
    
    # Verify the returned coupon
    claims = verify_coupon(data["coupon"])
    assert claims["aud"] == "test-service"
    assert claims["scope"] == "read:data"

def test_verify_coupon():
    # 1. Issue
    issue_resp = client.post(
        "/v1/issue",
        json={"audience": "test-service", "scope": "read:data"}
    )
    coupon = issue_resp.json()["coupon"]
    
    # 2. Verify
    # Mock redis for revocation check
    from unittest.mock import patch
    with patch("backend.services.revocation.redis_client") as mock_redis:
        mock_redis.exists.return_value = 0 # Not revoked
        
        verify_resp = client.post(
            "/v1/verify",
            json={"coupon": coupon}
        )
        assert verify_resp.status_code == 200
        assert verify_resp.json()["valid"] is True
        assert verify_resp.json()["claims"]["aud"] == "test-service"

def test_revoke_coupon():
    # 1. Issue
    issue_resp = client.post(
        "/v1/issue",
        json={"audience": "test-service", "scope": "read:data"}
    )
    data = issue_resp.json()
    coupon = data["coupon"]
    jti = data["jti"]
    
    # 2. Revoke
    from unittest.mock import patch
    with patch("backend.services.revocation.redis_client") as mock_redis:
        # Setup mock for setex (revoke) and exists (verify)
        mock_redis.exists.return_value = 1
        
        revoke_resp = client.post(
            "/v1/revoke",
            json={"jti": jti, "reason": "test"}
        )
        assert revoke_resp.status_code == 200
        assert revoke_resp.json()["status"] == "revoked"
        
        # 3. Verify (should fail)
        verify_resp = client.post(
            "/v1/verify",
            json={"coupon": coupon}
        )
        assert verify_resp.status_code == 200
        assert verify_resp.json()["valid"] is False
        assert verify_resp.json()["error"] == "revoked"
