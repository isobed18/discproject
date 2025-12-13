import sys
from jose import jwt
from datetime import datetime, timedelta

# Simple script to generate a dummy OIDC token for testing
# Usage: python create_test_token.py <subject>

def create_dummy_token(subject="test-user"):
    payload = {
        "iss": "https://accounts.google.com",
        "sub": subject,
        "aud": "disc-api",
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(hours=1),
        "name": f"Test User ({subject})",
        "email": f"{subject}@example.com"
    }
    # We sign with a dummy key because the backend currently (in MVP)
    # uses jwt.get_unverified_claims() or similar for OIDC.
    # If backend enforces signature, we'd need the shared secret.
    token = jwt.encode(payload, "secret-for-testing", algorithm="HS256")
    return token

if __name__ == "__main__":
    subject = sys.argv[1] if len(sys.argv) > 1 else "test-user"
    print(create_dummy_token(subject))
