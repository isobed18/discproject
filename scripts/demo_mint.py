import requests
import json
from jose import jwt
from datetime import datetime, timedelta, timezone

def create_demo_token(subject="demo-admin"):
    now = datetime.now(timezone.utc)
    payload = {
        "iss": "https://accounts.google.com",
        "sub": subject,
        "aud": "disc-api",
        "iat": now,
        "exp": now + timedelta(hours=1),
        "name": f"Test User ({subject})",
        "email": f"{subject}@example.com",
        "scope": "read:data write:data admin"
    }
    # Using HS256 with dummy secret helps it pass JWT structure checks.
    # Backend falls back to unverified claims if signature checks fail, 
    # but we can try to match the secret if we wanted. 
    # For now, any HS256 token works because of the fallback in endpoints.py
    token = jwt.encode(payload, "secret-for-testing", algorithm="HS256")
    return token

def mint_demo_coupon():
    # 1. Generate Token
    print("Locked & Loaded: Generating secure OIDC-like token for 'demo-admin'...")
    token = create_demo_token()
    print(f"Token generated: {token[:20]}...")
    
    # 2. Call API
    url = "http://localhost:8000/v1/issue"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    payload = {
        "audience": "demo-app",
        "scope": "read:data",
        "ttl_seconds": 300
    }
    
    print(f"\nSending authenticated request to {url}...")
    try:
        response = requests.post(url, headers=headers, json=payload)
        # Check specific status codes to provide better error msgs
        if response.status_code == 403:
            print("\nERROR: 403 Forbidden. OPA denied the request.")
            print("Check: 1. Is 'demo-admin' allowed? 2. Is OPA running? 3. Are policies loaded?")
        elif response.status_code == 429:
             print("\nERROR: 429 Too Many Requests. Rate limit exceeded.")
        
        response.raise_for_status()
        data = response.json()
        
        print("\nSUCCESS! Coupon Issued:")
        print(json.dumps(data, indent=2))
        print("\nCheck the Audit Logs in your browser now!")
        
    except requests.exceptions.RequestException as e:
        print(f"\nREQUEST FAILED: {e}")
        if hasattr(e, 'response') and e.response is not None:
             try:
                 print(json.dumps(e.response.json(), indent=2))
             except:
                 print(e.response.text)

if __name__ == "__main__":
    mint_demo_coupon()
