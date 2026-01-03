
import requests
import json
from jose import jwt
from datetime import datetime, timedelta, timezone
import uuid

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
        "scope": "read:data write:data admin",
        "role": "admin",
        "jti": str(uuid.uuid4())
    }
    # Using 'dev_secret_key_change_in_production' to match backend config
    token = jwt.encode(payload, "dev_secret_key_change_in_production", algorithm="HS256")
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
        
        if response.status_code == 403:
            print("\nERROR: 403 Forbidden. OPA denied the request.")
        elif response.status_code == 429:
             print("\nERROR: 429 Too Many Requests. Rate limit exceeded.")
        
        response.raise_for_status()
        data = response.json()
        
        print("\nSUCCESS! Coupon Issued:")
        print(json.dumps(data, indent=2))
        print("\nCheck the Audit Logs in your browser now!")
        
    except Exception as e:
        print(f"\nREQUEST FAILED: {e}")
        try:
             print(response.text)
        except:
             pass

if __name__ == "__main__":
    mint_demo_coupon()
