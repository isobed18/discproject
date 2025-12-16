import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
import pyseto
from pyseto import Key
from .config import settings
from jose import jwt, JWTError
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
import uuid

# --- Key Management ---
# For this MVP, we generate a new Ed25519 key pair on every startup.
# In Production, these keys should be loaded from a secure vault or env vars.

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

# Initialize Pyseto Keys (v4.public uses Ed25519)
private_key = Key.new(version=4, purpose="public", key=_priv_pem)
public_key = Key.new(version=4, purpose="public", key=_pub_pem)

# --- Core Functions ---

def create_coupon(
    subject: str, 
    audience: str, 
    scope: str, 
    ttl_seconds: int = 300,
    cnf: Optional[Dict[str, Any]] = None
) -> str:
    """
    Mints a new PASETO v4.public signed coupon.
    """
    now = datetime.now(timezone.utc)
    exp = now + timedelta(seconds=ttl_seconds)
    
    payload = {
        "iss": "disc-ca",
        "sub": subject,
        "aud": audience,
        "exp": exp.isoformat(),
        "iat": now.isoformat(),
        "nbf": now.isoformat(),
        "jti": str(uuid.uuid4()), # Unique identifier for revocation
        "scope": scope
    }
    
    # Add Proof-of-Possession (cnf) claim if provided
    if cnf:
        payload["cnf"] = cnf

    # Encode and sign
    token = pyseto.encode(private_key, payload)
    return token.decode("utf-8")

def verify_coupon(token: str) -> Dict[str, Any]:
    """
    Verifies the signature and standard claims (exp, nbf) of a PASETO token.
    Throws an exception if invalid.
    """
    try:
        decoded = pyseto.decode(public_key, token)
        return json.loads(decoded.payload) 
    except Exception as e:
        raise ValueError(f"Invalid token: {str(e)}")

def verify_oidc_token(token: str) -> Dict[str, Any]:
    """
    Parses an OIDC token to extract user identity.
    For MVP/Dev, this uses 'get_unverified_claims' to bypass signature checks
    since we don't have a real IdP connected.
    """
    try:
        return jwt.get_unverified_claims(token)
    except JWTError as e:
        raise ValueError(f"Invalid OIDC token: {str(e)}")

def get_mtls_identity(request_headers: Dict[str, str]) -> Optional[str]:
    """
    Extracts mTLS identity (cert hash) from request headers.
    This is usually passed by the ingress controller / load balancer.
    """
    # Look for common header X-Client-Cert-Hash
    cert_hash = request_headers.get("x-client-cert-hash")
    if cert_hash:
        return f"x5t#S256:{cert_hash}"
    return None