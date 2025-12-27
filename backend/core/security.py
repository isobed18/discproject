import json
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Optional
import pyseto
from pyseto import Key
from jose import jwt, JWTError
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization

# --- DÜZELTME: Absolute Import (Nokta yok!) ---
from core.config import settings
from cryptography.fernet import Fernet

# --- Encryption Utils (Week 4) ---
_fernet = Fernet(settings.FIELD_ENCRYPTION_KEY)

def encrypt_field(value: str) -> str:
    """Encrypts a string value using Fernet (AES)."""
    if not value:
        return value
    return _fernet.encrypt(value.encode()).decode()

def decrypt_field(token: str) -> str:
    """Decrypts a previously encrypted string."""
    if not token:
        return token
    return _fernet.decrypt(token.encode()).decode()


# --- Key Generation / Loading ---
# Week 5: Allow stable keys via env/.env so SDK can verify locally.


def _read_pem_from_path(path: Optional[str]) -> Optional[bytes]:
    if not path:
        return None
    p = Path(path).expanduser()
    if not p.exists() or not p.is_file():
        return None
    return p.read_bytes()


def _load_or_generate_keys() -> tuple[bytes, bytes]:
    # Priority: PEM strings -> file paths -> ephemeral generation
    priv_pem: Optional[bytes] = None
    pub_pem: Optional[bytes] = None

    if settings.PASETO_PRIVATE_KEY_PEM:
        priv_pem = settings.PASETO_PRIVATE_KEY_PEM.encode("utf-8")
    if settings.PASETO_PUBLIC_KEY_PEM:
        pub_pem = settings.PASETO_PUBLIC_KEY_PEM.encode("utf-8")

    if priv_pem is None:
        priv_pem = _read_pem_from_path(settings.PASETO_PRIVATE_KEY_PATH)
    if pub_pem is None:
        pub_pem = _read_pem_from_path(settings.PASETO_PUBLIC_KEY_PATH)

    if priv_pem:
        # Derive public key when not provided.
        try:
            priv_obj = serialization.load_pem_private_key(priv_pem, password=None)
            if pub_pem is None:
                pub_obj = priv_obj.public_key()
                pub_pem = pub_obj.public_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PublicFormat.SubjectPublicKeyInfo,
                )
        except Exception:
            # Fall back to generating ephemeral keys.
            priv_pem = None
            pub_pem = None

    if not priv_pem or not pub_pem:
        # Ephemeral (MVP) keys.
        _priv_key = ed25519.Ed25519PrivateKey.generate()
        priv_pem = _priv_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        pub_pem = _priv_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )

    return priv_pem, pub_pem


_priv_pem, _pub_pem = _load_or_generate_keys()

private_key = Key.new(version=4, purpose="public", key=_priv_pem)
public_key = Key.new(version=4, purpose="public", key=_pub_pem)


def get_public_key_pem() -> str:
    return _pub_pem.decode("utf-8")

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