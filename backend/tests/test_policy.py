import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from backend.main import app
from backend.core.policy import policy_engine


client = TestClient(app)

if __name__ == "__main__":
    # check if we can import
    print("Imports successful")
    # Manual test run
    try:
        # Mocking for manual run
        with patch("requests.post") as mock_post:
             mock_response = MagicMock()
             mock_response.status_code = 200
             mock_response.json.return_value = {"result": {"allow": True}}
             mock_post.return_value = mock_response
             
             payload = {"audience": "my-service", "scope": "read:data", "ttl_seconds": 300}
             print(f"Testing /v1/issue with payload: {payload}")
             response = client.post("/v1/issue", json=payload)
             print(f"Response: {response.status_code} {response.text}")
             assert response.status_code == 200
             print("SUCCESS: Issue allowed")

        with patch("requests.post") as mock_post:
             mock_response = MagicMock()
             mock_response.status_code = 200
             mock_response.json.return_value = {"result": {"allow": False}}
             mock_post.return_value = mock_response
             
             payload = {"audience": "restricted-service", "scope": "admin", "ttl_seconds": 300}
             print(f"Testing /v1/issue with payload: {payload}")
             response = client.post("/v1/issue", json=payload)
             print(f"Response: {response.status_code} {response.text}")
             assert response.status_code == 403
             print("SUCCESS: Issue denied")
             
    except Exception as e:
        print(f"FAILED: {e}")
        import traceback
        traceback.print_exc()

client = TestClient(app)


# Mock OPA responses
@pytest.fixture
def mock_opa_allow():
    with patch("requests.post") as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": {"allow": True}}
        mock_post.return_value = mock_response
        yield mock_post

@pytest.fixture
def mock_opa_deny():
    with patch("requests.post") as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": {"allow": False}}
        mock_post.return_value = mock_response
        yield mock_post

def test_issue_coupon_allowed(mock_opa_allow):
    """
    Test that issuance works when OPA returns allow=True.
    """
    payload = {
        "audience": "my-service",
        "scope": "read:data",
        "ttl_seconds": 300
    }
    response = client.post("/v1/issue", json=payload)
    assert response.status_code == 200
    assert "coupon" in response.json()
    
    # Verify we called OPA
    mock_opa_allow.assert_called_once()
    # Check that we passed the expected input structure
    call_args = mock_opa_allow.call_args
    assert "input" in call_args.kwargs['json']
    assert call_args.kwargs['json']['input']['audience'] == "my-service"

def test_issue_coupon_denied(mock_opa_deny):
    """
    Test that issuance fails (403) when OPA returns allow=False.
    """
    payload = {
        "audience": "restricted-service",
        "scope": "admin",
        "ttl_seconds": 300
    }
    response = client.post("/v1/issue", json=payload)
    assert response.status_code == 403
    assert response.json()["detail"] == "Policy denied by OPA"

def test_opa_connection_error():
    """
    Test fail-closed behavior if OPA is down.
    """
    with patch("requests.post", side_effect=Exception("Connection refused")):
        payload = {"audience": "any", "scope": "any"}
        response = client.post("/v1/issue", json=payload)
        assert response.status_code == 403
