# x25519_util.py
# Use the same pure-Python X25519 as the ESP32 (not cryptography.exchange).

import os

import x25519_pure as x25519


def generate_ephemeral_keypair() -> tuple:
    """Return (scalar_int, public_key_bytes)."""
    scalar = x25519.clamp_scalar(os.urandom(32))
    public = x25519.public_key_from_scalar(scalar)
    return scalar, public


def shared_secret(local_scalar: int, peer_public_bytes: bytes) -> bytes:
    return x25519.shared_secret(local_scalar, peer_public_bytes)


def make_nonce() -> bytes:
    return os.urandom(16)
