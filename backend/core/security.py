import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
import pyseto
from pyseto import Key
from .config import settings
from jose import jwt, JWTError

# For this MVP, we are using a symmetric key (v4.local) or asymmetric (v4.public)
# The design called for v4.public. We need a key pair.
# For simplicity in MVP, we will generate a key pair on startup if not provided, 
# or use a static seed for reproducibility in dev.

from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization

# Generate a key pair for v4.public (Ed25519)
_priv_key = ed25519.Ed25519PrivateKey.generate()
_priv_pem = _priv_key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption()
)
_pub_key = _priv_key.public_key()
_pub_pem = _pub_key.public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo
)

private_key = Key.new(version=4, purpose="public", key=_priv_pem)
public_key = Key.new(version=4, purpose="public", key=_pub_pem)

import uuid

# ...

def create_coupon(subject: str, audience: str, scope: str, ttl_seconds: int = 300, cnf: Optional[Dict[str, Any]] = None) -> str:
    now = datetime.now(timezone.utc)
    expire = now + timedelta(seconds=ttl_seconds)
    jti = str(uuid.uuid4())
    
    payload = {
        "iss": "disc-ca",
        "sub": subject,
        "aud": audience,
        "scope": scope,
        "exp": expire.isoformat(),
        "iat": now.isoformat(),
        "nbf": now.isoformat(),
        "jti": jti,
    }
    
    if cnf:
        payload["cnf"] = cnf

    token = pyseto.encode(
        private_key,
        payload,
    )
    return token.decode("utf-8")

def verify_coupon(token: str) -> Dict[str, Any]:
    try:
        decoded = pyseto.decode(
            public_key,
            token,
        )

        return json.loads(decoded.payload)
    except Exception as e:
        # In a real app, handle specific exceptions (Expired, InvalidSignature, etc.)
        raise ValueError(f"Invalid token: {str(e)}")

# ... (existing code)

def verify_oidc_token(token: str) -> Dict[str, Any]:
    """
    Verify OIDC token.
    For MVP, we just decode without verification if no JWKS is configured,
    or verify signature if we had the key.
    """
    try:
        # In a real app, you would fetch JWKS from the issuer and verify signature.
        # For this MVP/Local dev, we will just decode unverified to extract claims,
        # assuming the token came from a trusted source (or we mock it).
        # If SECRET_KEY is used for OIDC (HS256), we can verify.
        
        # Let's assume for MVP we just check if it's a valid JWT structure
        # and return the payload.
        payload = jwt.get_unverified_claims(token)
        return payload
    except JWTError as e:
        raise ValueError(f"Invalid OIDC token: {str(e)}")

def get_mtls_identity(request_headers: Dict[str, str]) -> Optional[str]:
    """
    Extract mTLS identity from headers (e.g., X-Client-Cert-Hash or X-Subject-DN).
    """
    # Common headers used by proxies (Nginx/Envoy)
    # X-Client-Cert-Hash (SHA256 fingerprint)
    # X-Client-DN (Distinguished Name)
    
    cert_hash = request_headers.get("x-client-cert-hash")
    if cert_hash:
        return f"x5t#S256:{cert_hash}"
        
    return None
