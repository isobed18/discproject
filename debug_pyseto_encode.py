import pyseto
from pyseto import Key
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization

_priv_key = ed25519.Ed25519PrivateKey.generate()
_priv_pem = _priv_key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption()
)
private_key = Key.new(version=4, purpose="public", key=_priv_pem)

token = pyseto.encode(private_key, {"sub": "test"})
print(f"Type: {type(token)}")
print(f"Value: {token}")
