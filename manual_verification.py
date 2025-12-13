import requests
import json
import sys

BASE_URL = "http://localhost:8003/v1"

def test_flow():
    print("--- 1. Testing Delegation ---")
    d_payload = {"delegate": "ali", "resource": "secure-doc-1", "ttl": 3600}
    try:
        d_res = requests.post(f"{BASE_URL}/delegations", json=d_payload)
        print(f"Delegation Status: {d_res.status_code} {d_res.text}")
    except Exception as e:
        print(f"Failed to connect: {e}")
        return

    print("\n--- 2. Testing Issue Coupon (Allowed via Delegation) ---")
    # For MVP OPA logic, we might need 'sub' to match 'delegate' in the policy check.
    # Our policy mock assumes 'sub' comes from OIDC token.
    # If we don't send a token, endpoints.py might default strictly or fail.
    # Let's try sending a mock token if possible, or assume endpoints defaults to "anonymous" or "test-user".
    # BUT, we delegated to "ali". So we need to BE "ali".
    # In endpoints.py, user_id defaults to "anonymous".
    # If we want to be "ali", we need to fake the OIDC token parsing or change the delegation to "anonymous" for this test.
    
    # Wait, endpoints.py: 
    # user_id = "anonymous"
    # if authorization: ... claims = verify_oidc_token(token) ... user_id = claims.get("sub")
    
    # Since we can't easily generate a valid signed OIDC token that verify_oidc_token accepts (it verifies signature),
    # verifying "ali" specifically is hard without a real IDP.
    # HOWEVER, we can Delegate to "anonymous" to test the flow!
    
    d_payload_anon = {"delegate": "anonymous", "resource": "secure-doc-1", "ttl": 3600}
    requests.post(f"{BASE_URL}/delegations", json=d_payload_anon)
    print("(Added delegation for 'anonymous' just in case)")

    i_payload = {"audience": "app-srv", "scope": "read", "resource": "secure-doc-1"}
    i_res = requests.post(f"{BASE_URL}/issue", json=i_payload)
    print(f"Issue Status: {i_res.status_code}")
    if i_res.status_code == 200:
        print(f"Coupon: {i_res.json().get('coupon')[:20]}...")
    else:
        print(f"Error: {i_res.text}")

    print("\n--- 3. Testing Partial Evaluation ---")
    # Should get 'secure-doc-1' back, but NOT 'forbidden-doc-99'
    p_payload = {"resources": ["secure-doc-1", "forbidden-doc-99"], "action": "read", "audience": "app-srv"}
    p_res = requests.post(f"{BASE_URL}/filter-authorized", json=p_payload)
    print(f"Partial Eval Result: {p_res.json()}")

if __name__ == "__main__":
    test_flow()
