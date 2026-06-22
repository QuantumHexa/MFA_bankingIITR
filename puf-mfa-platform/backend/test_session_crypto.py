"""Ratcheting session key roundtrip — server derives without receiving the key."""

from app.services.session_crypto import (
    decrypt_transaction_payload,
    derive_session_root,
    derive_txn_key,
    encrypt_transaction_payload,
)


def test_ratchet_encrypt_decrypt_roundtrip():
    proof = "a" * 64
    login_id = "session-uuid-1234"
    nonce = "b" * 32
    challenge = "c" * 32
    session_id = login_id

    root = derive_session_root(
        proof_hex=proof,
        login_id=login_id,
        nonce=nonce,
        challenge=challenge,
        session_id=session_id,
    )

    payload = b'{"type":"transfer","amount":100}'
    enc = encrypt_transaction_payload(root, counter=0, plaintext=payload)
    plain = decrypt_transaction_payload(root, 0, enc["iv"], enc["ciphertext"])
    assert plain == payload

    k1 = derive_txn_key(root, 0)
    k2 = derive_txn_key(root, 1)
    assert k1 != k2


if __name__ == "__main__":
    test_ratchet_encrypt_decrypt_roundtrip()
    print("OK")
