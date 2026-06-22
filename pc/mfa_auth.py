# mfa_auth.py

import hmac
import hashlib

import protocol


def build_transcript(login_id: str, customer_id: str, nonce: bytes) -> bytes:
    return (
        protocol.MFA_PROOF_INFO
        + b"|"
        + login_id.encode()
        + b"|"
        + customer_id.encode()
        + b"|"
        + nonce
    )


def compute_login_proof(shared_secret: bytes, login_id: str, customer_id: str, nonce: bytes) -> bytes:
    transcript = build_transcript(login_id, customer_id, nonce)
    return hmac.new(shared_secret, transcript, hashlib.sha256).digest()


def verify_login_proof(
    shared_secret: bytes,
    login_id: str,
    customer_id: str,
    nonce: bytes,
    proof: bytes,
) -> None:
    expected = compute_login_proof(shared_secret, login_id, customer_id, nonce)
    if not hmac.compare_digest(expected, proof):
        raise ValueError("MFA device proof verification FAILED")
