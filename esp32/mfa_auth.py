# mfa_auth.py
# Login proof = HMAC-SHA256(shared_ecdh_secret, domain-separated transcript).

from hkdf import _hmac_sha256
import config

PROOF_INFO = getattr(config, "MFA_PROOF_INFO", b"esp32c6-mfa-login-proof-v1")


def build_transcript(login_id, customer_id, nonce_bytes):
    return (
        PROOF_INFO
        + b"|"
        + login_id.encode()
        + b"|"
        + customer_id.encode()
        + b"|"
        + nonce_bytes
    )


def compute_login_proof(shared_secret, login_id, customer_id, nonce_bytes):
    transcript = build_transcript(login_id, customer_id, nonce_bytes)
    return _hmac_sha256(shared_secret, transcript)
