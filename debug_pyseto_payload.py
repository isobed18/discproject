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
private_key = Key.new(version=4, purpose="public", key=_priv_pem)

token = pyseto.encode(private_key, {"sub": "test"})
decoded = pyseto.decode(private_key, token) # Using private key to decode/verify works for v4.public? usually need public key but let's see.
# Wait, decode needs public key for verification.
_pub_key = _priv_key.public_key()
_pub_pem = _pub_key.public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo
)
public_key = Key.new(version=4, purpose="public", key=_pub_pem)
decoded = pyseto.decode(public_key, token)

print(f"Payload type: {type(decoded.payload)}")
print(f"Payload: {decoded.payload}")
