"""Crypto round-trip sanity check for encrypted registration."""
import base64
import json
import os
import sys

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

sys.path.insert(0, os.path.dirname(__file__))

from app.crypto import decrypt_registration_payload, get_public_key_pem, load_or_generate_keypair

load_or_generate_keypair("")
pub_pem = get_public_key_pem()
pub_key = serialization.load_pem_public_key(pub_pem.encode())

aes_key = os.urandom(32)
iv = os.urandom(12)
payload = json.dumps(
    {
        "username": "encuser01",
        "email": "encuser01@example.com",
        "phone": "7300041850",
        "full_name": "Enc User",
        "dob": "2000-01-01",
        "initial_deposit": 1000,
        "netbanking_enabled": True,
        "password": "TestPass123",
        "puf_enabled": False,
        "puf_mode": "virtual",
    }
).encode()
ciphertext = AESGCM(aes_key).encrypt(iv, payload, None)

encrypted_key = pub_key.encrypt(
    aes_key,
    padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None),
)

result = decrypt_registration_payload(
    base64.b64encode(encrypted_key).decode(),
    base64.b64encode(iv).decode(),
    base64.b64encode(ciphertext).decode(),
)
assert result["username"] == "encuser01"
print("crypto round-trip passed")
