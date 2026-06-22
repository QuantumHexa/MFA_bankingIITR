"""Encrypted transaction endpoint — server derives ratchet keys from stored MFA proof."""

from __future__ import annotations

import json
from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.database import SessionCryptoState
from app.deps import CurrentUser, DbSession
from app.services.session_crypto import decrypt_transaction_payload, derive_session_root

router = APIRouter()


class EncryptedTransferRequest(BaseModel):
    crypto_session_id: str
    counter: int = Field(..., ge=0)
    iv: str
    ciphertext: str


@router.post("/transfer")
def decrypt_transfer(payload: EncryptedTransferRequest, user: CurrentUser, db: DbSession) -> dict:
    """Decrypt a ratcheted transaction blob. Server never receives the session key."""
    state = (
        db.query(SessionCryptoState)
        .filter(SessionCryptoState.id == payload.crypto_session_id, SessionCryptoState.user_id == user.id)
        .first()
    )
    if not state:
        raise HTTPException(status_code=404, detail="Crypto session not found")
    if datetime.utcnow() > state.expires_at:
        raise HTTPException(status_code=400, detail="Crypto session expired — log in again")

    if payload.counter != state.ratchet_counter:
        raise HTTPException(
            status_code=409,
            detail=f"Ratchet counter mismatch (expected {state.ratchet_counter}, got {payload.counter})",
        )

    root = derive_session_root(
        proof_hex=state.proof_hex,
        login_id=state.auth_session_id,
        nonce=state.nonce,
        challenge=state.challenge,
        session_id=state.auth_session_id,
    )

    try:
        plaintext = decrypt_transaction_payload(root, payload.counter, payload.iv, payload.ciphertext)
        txn = json.loads(plaintext.decode())
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Decryption failed: {exc}") from exc

    state.ratchet_counter += 1
    db.commit()

    return {
        "status": "success",
        "message": "Transaction decrypted with ratcheted session key",
        "transaction": txn,
        "next_counter": state.ratchet_counter,
        "ratchet_note": "Next transfer must use the incremented counter",
    }


@router.get("/crypto-session")
def active_crypto_session(user: CurrentUser, db: DbSession) -> dict:
    """Return active crypto session metadata for the logged-in user."""
    state = (
        db.query(SessionCryptoState)
        .filter(SessionCryptoState.user_id == user.id, SessionCryptoState.expires_at > datetime.utcnow())
        .order_by(SessionCryptoState.created_at.desc())
        .first()
    )
    if not state:
        return {"active": False}
    return {
        "active": True,
        "crypto_session_id": state.id,
        "auth_session_id": state.auth_session_id,
        "ratchet_counter": state.ratchet_counter,
        "puf_mode": state.puf_mode,
        "expires_at": state.expires_at.isoformat() + "Z",
    }
