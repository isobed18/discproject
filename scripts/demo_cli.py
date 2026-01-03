
import argparse
import requests
import sys
import json

# Configuration
BASE_URL = "http://localhost:8000/v1"

def issue_token(audience="demo-cli", scope="read:data"):
    """Simulates: disc-cli issue --audience ..."""
    print(f"👉 CLI: Requesting new token (Aud: {audience}, Scope: {scope})...")
    
    # Normally CLI authenticates via OIDC. Here we simulate the result of a successful auth.
    # We use the 'mint' endpoint logic or similar.
    # To keep it simple for the demo, we'll use the same logic as demo_mint.py to generate a 'user' token 
    # and then exchange it or just call issue directly if allowed.
    # Wait, /issue requires Authentication. 
    # We'll use the 'demo_mint' logic (self-signed jwt) to authenticate the CLI to the Backend.
    
    from jose import jwt
    from datetime import datetime, timedelta, timezone
    import uuid

    # 1. Create a transient Identity Token (like an ID Token from Google)
    secret = "dev_secret_key_change_in_production"
    now = datetime.now(timezone.utc)
    id_token = jwt.encode({
        "sub": "cli-user",
        "aud": "disc-api",
        "iat": now,
        "exp": now + timedelta(minutes=5),
        "name": "CLI User",
        "scope": "read:data write:data"
    }, secret, algorithm="HS256")

    # 2. Call /issue
    try:
        resp = requests.post(f"{BASE_URL}/issue", 
                             json={"audience": audience, "scope": scope, "ttl_seconds": 3600},
                             headers={"Authorization": f"Bearer {id_token}"})
        resp.raise_for_status()
        data = resp.json()
        
        print("\n✅ TOKEN ISSUED SUCCESSFULLY:")
        print(f"Coupon (Token): {data['coupon']}")
        print(f"Expires In: {data['expires_in']}s")
        print(f"JTI: {data['jti']}")
        
        # Save to temp file for next step
        with open("last_token.txt", "w") as f:
            f.write(data['coupon'])
        print("\n(Token saved to last_token.txt for verification step)")
        
    except Exception as e:
        print(f"❌ Failed to issue token: {e}")
        try: print(resp.text)
        except: pass

def verify_token(token=None):
    """Simulates: disc-cli verify --token ..."""
    if not token:
        try:
            with open("last_token.txt", "r") as f:
                token = f.read().strip()
            print("👉 CLI: Verifying token from last session (last_token.txt)...")
        except:
            print("❌ No token provided and no last_token.txt found.")
            return

    print(f"Requesting verification for token: {token[:15]}...")
    
    try:
        resp = requests.post(f"{BASE_URL}/verify", json={"coupon": token})
        data = resp.json()
        
        if data.get("valid"):
            print("\n✅ STATUS: VALID")
            print("Claims:", json.dumps(data.get("claims"), indent=2))
        else:
            print("\n❌ STATUS: INVALID/REVOKED")
            print("Error:", data.get("error"))

    except Exception as e:
        print(f"❌ Verification failed (Network/Server error): {e}")

def main():
    parser = argparse.ArgumentParser(description="DISC CLI Tool Simulator")
    subparsers = parser.add_subparsers(dest="command")
    
    issue_parser = subparsers.add_parser("issue", help="Issue a new token")
    issue_parser.add_argument("--audience", default="demo-cli")
    
    verify_parser = subparsers.add_parser("verify", help="Verify a token")
    verify_parser.add_argument("token", nargs="?", help="Token to verify (optional if issued previously)")
    
    args = parser.parse_args()
    
    if args.command == "issue":
        issue_token(audience=args.audience)
    elif args.command == "verify":
        verify_token(token=args.token)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
