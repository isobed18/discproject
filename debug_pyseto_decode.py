import pyseto
from pyseto import Key
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization

# Setup keys
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

# Encode
token_bytes = pyseto.encode(private_key, {"sub": "test"})
token_str = token_bytes.decode("utf-8")

print(f"Token str: {token_str}")

# Decode with str
try:
    decoded = pyseto.decode(public_key, token_str)
    print("Decode with str successful")
except Exception as e:
    print(f"Decode with str failed: {e}")

# Decode with bytes
try:
    decoded = pyseto.decode(public_key, token_bytes)
    print("Decode with bytes successful")
except Exception as e:
    print(f"Decode with bytes failed: {e}")
