"""HKDF session-root + ratcheting transaction keys after hardware MFA proof.

Neither side transmits the session key. Both derive:
  root = HKDF-SHA256(ikm=proof||login_id||nonce||challenge, salt=session_id)
  txn_key[n] = HKDF-SHA256(ikm=root, salt=counter, info=b"securevault-txn-v1")
"""

from __future__ import annotations

import base64
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

ROOT_INFO = b"securevault-session-root-v1"
TXN_INFO = b"securevault-txn-v1"


def _hkdf(ikm: bytes, *, salt: bytes, info: bytes, length: int = 32) -> bytes:
    return HKDF(algorithm=hashes.SHA256(), length=length, salt=salt, info=info).derive(ikm)


def derive_session_root(
    *,
    proof_hex: str,
    login_id: str,
    nonce: str,
    challenge: str,
    session_id: str,
) -> bytes:
    ikm = f"{proof_hex}:{login_id}:{nonce}:{challenge}".encode()
    return _hkdf(ikm, salt=session_id.encode(), info=ROOT_INFO)


def derive_txn_key(root: bytes, counter: int) -> bytes:
    if counter < 0:
        raise ValueError("counter must be non-negative")
    return _hkdf(root, salt=counter.to_bytes(4, "big"), info=TXN_INFO)


def encrypt_transaction_payload(root: bytes, counter: int, plaintext: bytes) -> dict:
    key = derive_txn_key(root, counter)
    iv = os.urandom(12)
    ciphertext = AESGCM(key).encrypt(iv, plaintext, counter.to_bytes(4, "big"))
    return {
        "counter": counter,
        "iv": base64.b64encode(iv).decode(),
        "ciphertext": base64.b64encode(ciphertext).decode(),
    }


def decrypt_transaction_payload(root: bytes, counter: int, iv_b64: str, ciphertext_b64: str) -> bytes:
    key = derive_txn_key(root, counter)
    iv = base64.b64decode(iv_b64)
    ciphertext = base64.b64decode(ciphertext_b64)
    return AESGCM(key).decrypt(iv, ciphertext, counter.to_bytes(4, "big"))
