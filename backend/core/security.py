import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
import pyseto
from pyseto import Key
from jose import jwt, JWTError
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization

# --- DÜZELTME: Absolute Import (Nokta yok!) ---
from core.config import settings

# --- Key Generation (Memory-based for MVP) ---
# Bu anahtarlar her restartta değişir (MVP için normal)
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

def create_coupon(subject: str, audience: str, scope: str, ttl_seconds: int = 300, cnf: Dict[str, Any] = None) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "iss": "https://auth.disc.local",
        "sub": subject,
        "aud": audience,
        "exp": (now + timedelta(seconds=ttl_seconds)).isoformat(),
        "nbf": now.isoformat(),
        "iat": now.isoformat(),
        "jti": str(uuid.uuid4()),
        "scope": scope
    }
    if cnf:
        payload["cnf"] = cnf

    token = pyseto.encode(
        private_key,
        payload,
        footer={"kid": "v4.public"}
    )
    return token.decode("utf-8")

def verify_coupon(token: str) -> Dict[str, Any]:
    try:
        decoded = pyseto.decode(public_key, token)
        return json.loads(decoded.payload)
    except Exception as e:
        raise ValueError(f"Invalid token: {str(e)}")

def verify_oidc_token(token: str) -> Dict[str, Any]:
    # Mock validation for MVP
    try:
        payload = jwt.get_unverified_claims(token)
        return payload
    except JWTError as e:
        raise ValueError(f"Invalid OIDC token: {str(e)}")

def get_mtls_identity(request_headers: Dict[str, str]) -> Optional[str]:
    cert_hash = request_headers.get("x-client-cert-hash")
    if cert_hash:
        return f"x5t#S256:{cert_hash}"
    return None