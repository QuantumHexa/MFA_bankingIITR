"""E2E API test: public-key + encrypted signup + admin login."""
import base64
import json
import os
import secrets
import sys

import requests
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

BASE = "http://127.0.0.1:8002"

r = requests.get(f"{BASE}/api/auth/public-key", timeout=10)
print("public-key", r.status_code)
assert r.status_code == 200
pub_pem = r.json()["public_key_pem"]
assert pub_pem.startswith("-----BEGIN PUBLIC KEY-----")

pub_key = serialization.load_pem_public_key(pub_pem.encode())
uid = secrets.token_hex(4)
payload = {
    "username": f"user{uid}",
    "email": f"user{uid}@example.com",
    "phone": "7300041850",
    "full_name": "Encrypted User",
    "dob": "1999-05-15",
    "initial_deposit": 2500,
    "netbanking_enabled": True,
    "password": "SecurePass123",
    "puf_enabled": False,
    "puf_mode": "virtual",
}

aes_key = os.urandom(32)
iv = os.urandom(12)
ciphertext = AESGCM(aes_key).encrypt(iv, json.dumps(payload).encode(), None)
encrypted_key = pub_key.encrypt(
    aes_key,
    padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None),
)

body = {
    "encrypted_key": base64.b64encode(encrypted_key).decode(),
    "iv": base64.b64encode(iv).decode(),
    "ciphertext": base64.b64encode(ciphertext).decode(),
}

r2 = requests.post(f"{BASE}/api/auth/signup", json=body, timeout=15)
print("encrypted signup", r2.status_code, r2.text[:200])
assert r2.status_code == 200, r2.text
assert r2.json()["message"] == "Account created."

# Plaintext signup must fail
r3 = requests.post(f"{BASE}/api/auth/signup", json=payload, timeout=10)
print("plaintext signup (should fail)", r3.status_code)
assert r3.status_code == 422

# Login unchanged
r4 = requests.post(
    f"{BASE}/api/auth/login/start",
    json={"username": "admin", "password": "admin"},
    timeout=10,
)
print("admin login", r4.status_code)
assert r4.status_code == 200

print("E2E encrypted registration tests passed")
