"""Application-layer hybrid encryption helpers.

Scheme: RSA-4096-OAEP-SHA256 wraps an ephemeral AES-256-GCM key.
The private key is loaded once at startup and kept in memory only.
"""

from __future__ import annotations

import json
from base64 import b64decode
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

_private_key: rsa.RSAPrivateKey | None = None
_public_key_pem: str = ""


def load_or_generate_keypair(private_key_path: str = "") -> None:
    """Load RSA-4096 private key from disk or generate a new key-pair."""
    global _private_key, _public_key_pem  # noqa: PLW0603

    if private_key_path and Path(private_key_path).exists():
        pem_bytes = Path(private_key_path).read_bytes()
        loaded = serialization.load_pem_private_key(pem_bytes, password=None)
        if not isinstance(loaded, rsa.RSAPrivateKey):
            raise RuntimeError("RSA private key required")
        _private_key = loaded
    else:
        _private_key = rsa.generate_private_key(public_exponent=65537, key_size=4096)
        if private_key_path:
            pem_bytes = _private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption(),
            )
            Path(private_key_path).write_bytes(pem_bytes)

    _public_key_pem = (
        _private_key.public_key()
        .public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode()
    )


def get_public_key_pem() -> str:
    if not _public_key_pem:
        raise RuntimeError("Keypair not loaded — call load_or_generate_keypair() at startup.")
    return _public_key_pem


def decrypt_registration_payload(
    encrypted_key_b64: str,
    iv_b64: str,
    ciphertext_b64: str,
) -> dict[str, Any]:
    if _private_key is None:
        raise RuntimeError("Keypair not loaded.")

    try:
        aes_key = _private_key.decrypt(
            b64decode(encrypted_key_b64),
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )
    except Exception as exc:
        raise ValueError(f"RSA decryption failed: {exc}") from exc

    try:
        aesgcm = AESGCM(aes_key)
        plaintext = aesgcm.decrypt(b64decode(iv_b64), b64decode(ciphertext_b64), None)
    except Exception as exc:
        raise ValueError(f"AES-GCM decryption/authentication failed: {exc}") from exc

    try:
        parsed = json.loads(plaintext.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Decrypted payload is not valid JSON: {exc}") from exc

    if not isinstance(parsed, dict):
        raise ValueError("Decrypted payload must be a JSON object")
    return parsed
