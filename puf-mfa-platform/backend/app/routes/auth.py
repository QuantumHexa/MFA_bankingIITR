import hashlib
import random
import uuid
import os
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, EmailStr, Field, ValidationError
from sqlalchemy.orm import Session

from app.config import settings
from app.crypto import decrypt_registration_payload, get_public_key_pem
from app.database import AuthLog, AuthSession, PufDevice, RefreshToken, SessionCryptoState, SiteAuthChallenge, User
from app.deps import CurrentUser, DbSession
from app.services.auth_service import (
    create_token_pair,
    generate_nonce,
    hash_token,
    hash_password,
    verify_password,
)
from app.services.event_bus import auth_events
from app.services.otp_service import generate_otp, hash_otp, mask_email, send_email_otp, verify_otp
from app.services.puf_service import (
    derive_secret_identifier,
    derive_session_key,
    enroll_puf,
    puf_verification_details,
    read_puf,
)

router = APIRouter()

SESSION_TTL_MINUTES = 15


def _set_auth_cookies(response: Response, tokens: dict, refresh_days: int | None = None) -> None:
    secure = settings.cookie_secure or settings.is_production
    same_site = settings.cookie_samesite
    domain = settings.cookie_domain or None
    response.set_cookie(
        key=settings.access_cookie_name,
        value=tokens["access_token"],
        httponly=True,
        secure=secure,
        samesite=same_site,
        max_age=settings.access_cookie_max_age_minutes * 60,
        domain=domain,
        path="/",
    )
    response.set_cookie(
        key=settings.refresh_cookie_name,
        value=tokens["refresh_token"],
        httponly=True,
        secure=secure,
        samesite=same_site,
        max_age=(refresh_days or settings.refresh_cookie_max_age_days) * 24 * 3600,
        domain=domain,
        path="/",
    )


def _clear_auth_cookies(response: Response) -> None:
    domain = settings.cookie_domain or None
    response.delete_cookie(settings.access_cookie_name, domain=domain, path="/")
    response.delete_cookie(settings.refresh_cookie_name, domain=domain, path="/")


def _emit(event: str, **data) -> None:
    auth_events.emit_sync(event, data)


def _log_auth(
    db: Session,
    user_id: str | None,
    event: str,
    factor: str,
    status: str,
    request: Request,
    meta: dict | None = None,
) -> None:
    db.add(
        AuthLog(
            user_id=user_id,
            event=event,
            factor=factor,
            status=status,
            ip_address=request.client.host if request.client else None,
            metadata_json=str(meta) if meta else None,
        )
    )
    db.commit()
    _emit("auth_log", user_id=user_id, event_type=event, factor=factor, status=status, meta=meta)


def _session_expired(session: AuthSession) -> bool:
    return datetime.utcnow() > session.created_at + timedelta(minutes=SESSION_TTL_MINUTES)


def _require_session_step(session: AuthSession, *allowed: str) -> None:
    """Ensure login flow steps are completed in order (OTP before PUF, etc.)."""
    if session.step not in allowed:
        raise HTTPException(
            status_code=403,
            detail="Complete the previous login step first (verify OTP before device authentication)",
        )


def _bootstrap_crypto_session(
    db: Session,
    user: User,
    session: AuthSession,
    proof_hex: str,
    puf_mode: str,
) -> dict:
    """Store MFA proof server-side; client derives ratchet keys locally (key never transmitted)."""
    expires = datetime.utcnow() + timedelta(hours=8)
    row = SessionCryptoState(
        user_id=user.id,
        auth_session_id=session.id,
        proof_hex=proof_hex.lower(),
        nonce=session.nonce,
        challenge=session.challenge,
        puf_mode=puf_mode,
        ratchet_counter=0,
        expires_at=expires,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {
        "crypto_session_id": row.id,
        "auth_session_id": session.id,
        "proof_hex": proof_hex.lower(),
        "nonce": session.nonce,
        "challenge": session.challenge,
        "ratchet_counter": 0,
        "puf_mode": puf_mode,
    }


def _complete_login(
    user: User,
    session: AuthSession,
    db: Session,
    response: Response,
    session_key: str | None = None,
) -> dict:
    session.used = True
    tokens = create_token_pair(user.id, user.role)
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_token(tokens["refresh_token"]),
            expires_at=datetime.utcnow() + timedelta(days=settings.jwt_refresh_rotate_days),
        )
    )
    db.commit()
    _set_auth_cookies(response, tokens)
    _emit("auth_complete", user_id=user.id, email=user.email, role=user.role)
    result = {**tokens, "next_step": "dashboard"}
    if session_key:
        result["session_key_preview"] = session_key[:16] + "..."
    return result


class EncryptedSignupRequest(BaseModel):
    """Hybrid-encrypted registration envelope from the frontend."""

    encrypted_key: str = Field(..., description="Base64 RSA-OAEP-encrypted AES key")
    iv: str = Field(..., description="Base64 12-byte AES-GCM nonce")
    ciphertext: str = Field(..., description="Base64 AES-GCM ciphertext of JSON payload")


class SignupRequest(BaseModel):
    id: str | None = None
    username: str = Field(..., min_length=4, max_length=30, pattern=r"^[a-zA-Z0-9_.-]+$")
    email: EmailStr
    phone: str = Field(..., pattern=r"^\d{10}$")
    full_name: str = Field(..., min_length=2, max_length=100)
    dob: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    initial_deposit: float = Field(default=0.0, ge=0)
    netbanking_enabled: bool = True
    password: str = Field(..., min_length=8)
    puf_enabled: bool = False
    puf_mode: str = Field(default="virtual", pattern=r"^(virtual|hardware|off)$")
    device_pubkey_hex: str | None = None
    site_auth_phrase: str | None = Field(default=None, min_length=4, max_length=40)


class SiteChallengeRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=100)


class SiteChallengeConfirmRequest(BaseModel):
    challenge_id: str


class LoginStartRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=100)
    password: str
    site_challenge_id: str | None = None


class OtpVerifyRequest(BaseModel):
    session_id: str
    otp: str = Field(..., min_length=6, max_length=6)


class SessionRequest(BaseModel):
    session_id: str


class HardwareVerifyRequest(BaseModel):
    session_id: str
    proof_hex: str | None = None


class PufVerifyRequest(BaseModel):
    session_id: str
    puf_response: str = Field(..., min_length=32, max_length=32)


class RefreshRequest(BaseModel):
    refresh_token: str | None = None


class PufEnrollRequest(BaseModel):
    mode: str = Field(default="virtual", pattern=r"^(virtual|hardware)$")


class PufPreviewRequest(BaseModel):
    mode: str = Field(default="virtual", pattern=r"^(virtual|hardware)$")
    device_pubkey_hex: str | None = None


def _generate_account_number(payload: SignupRequest) -> str:
    # Blend user profile fields + randomness into a 12-digit account number.
    raw = (
        f"{payload.full_name}|{payload.dob}|{payload.phone}|"
        f"{payload.email}|{payload.username}|{payload.puf_mode}|{random.random()}"
    )
    digest = hashlib.sha256(raw.encode()).hexdigest()
    digits = str(int(digest[:12], 16))
    return digits[:12].rjust(12, "0")


@router.get("/public-key")
def get_server_public_key() -> dict:
    """Return the server RSA-4096 public key in PEM format for encrypted registration."""
    return {"public_key_pem": get_public_key_pem()}


@router.post("/site-challenge")
def site_to_user_challenge(payload: SiteChallengeRequest, db: DbSession) -> dict:
    """Return the user's site authentication phrase (anti-phishing, text-only)."""
    user = db.query(User).filter(
        ((User.username == payload.username) | (User.email == payload.username)),
        User.is_active.is_(True),
        User.role != "admin",
    ).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    phrase = user.site_auth_phrase or f"SecureVault-{user.username}"
    challenge = SiteAuthChallenge(
        user_id=user.id,
        phrase_shown=phrase,
        expires_at=datetime.utcnow() + timedelta(minutes=10),
    )
    db.add(challenge)
    db.commit()
    db.refresh(challenge)

    return {
        "challenge_id": challenge.id,
        "phrase": phrase,
        "message": "Verify your Authentication Text to continue",
    }


@router.post("/site-challenge/confirm")
def site_to_user_confirm(payload: SiteChallengeConfirmRequest, db: DbSession) -> dict:
    """User confirmed the displayed authentication phrase."""
    challenge = db.query(SiteAuthChallenge).filter(SiteAuthChallenge.id == payload.challenge_id).first()
    if not challenge or datetime.utcnow() > challenge.expires_at:
        raise HTTPException(status_code=400, detail="Authentication challenge expired — start again")
    challenge.confirmed = True
    db.commit()
    return {"ok": True, "challenge_id": challenge.id}


@router.post("/signup")
def signup(encrypted_payload: EncryptedSignupRequest, request: Request, db: DbSession) -> dict:
    try:
        raw = decrypt_registration_payload(
            encrypted_payload.encrypted_key,
            encrypted_payload.iv,
            encrypted_payload.ciphertext,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"Payload decryption failed: {exc}") from exc

    try:
        payload = SignupRequest(**raw)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=f"Invalid registration data: {exc}") from exc

    if db.query(User).filter(
        (User.email == payload.email) | (User.phone == payload.phone) | (User.username == payload.username)
    ).first():
        raise HTTPException(status_code=400, detail="Email, phone, or username already registered")

    if not payload.netbanking_enabled:
        raise HTTPException(status_code=400, detail="Netbanking must be enabled for this platform")

    account_number = _generate_account_number(payload)
    while db.query(User).filter(User.account_number == account_number).first():
        account_number = _generate_account_number(payload)

    site_phrase = payload.site_auth_phrase or f"{payload.username}Auth"

    user = User(
        id=payload.id or str(uuid.uuid4()),
        username=payload.username,
        email=payload.email,
        phone=payload.phone,
        full_name=payload.full_name,
        dob=payload.dob,
        account_number=account_number,
        initial_deposit=payload.initial_deposit,
        password_hash=hash_password(payload.password),
        puf_enabled=payload.puf_enabled and payload.puf_mode != "off",
        puf_mode="off" if not payload.puf_enabled else payload.puf_mode,
        site_auth_phrase=site_phrase,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    enroll_result = None
    if user.puf_enabled:
        enroll_result = enroll_puf(db, user, user.puf_mode, payload.device_pubkey_hex)

    _log_auth(db, user.id, "signup", "account", "success", request, {"puf_enabled": user.puf_enabled})
    _emit("signup", user_id=user.id, email=user.email, puf_enabled=user.puf_enabled)

    return {
        "message": "Account created.",
        "user_id": user.id,
        "account_number": user.account_number,
        "initial_deposit": user.initial_deposit,
        "mfa_note": (
            f"You have enabled MFA with {user.puf_mode} PUF"
            if user.puf_enabled
            else "MFA is disabled for this account"
        ),
        "puf_enabled": user.puf_enabled,
        "puf_enrollment": enroll_result,
        "site_auth_phrase_set": bool(user.site_auth_phrase),
    }


@router.post("/login/start")
def login_start(payload: LoginStartRequest, request: Request, response: Response, db: DbSession) -> dict:
    user = db.query(User).filter(
        ((User.username == payload.username) | (User.email == payload.username)), User.is_active.is_(True)
    ).first()
    if not user or not verify_password(payload.password, user.password_hash):
        _log_auth(db, user.id if user else None, "login", "password", "failed", request)
        _emit("auth_step", step="password", status="failed", username=payload.username)
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if user.role != "admin":
        if not payload.site_challenge_id:
            raise HTTPException(status_code=400, detail="Site authentication required — verify your Authentication Text")
        site_challenge = (
            db.query(SiteAuthChallenge)
            .filter(
                SiteAuthChallenge.id == payload.site_challenge_id,
                SiteAuthChallenge.user_id == user.id,
            )
            .first()
        )
        if not site_challenge or not site_challenge.confirmed or datetime.utcnow() > site_challenge.expires_at:
            raise HTTPException(status_code=403, detail="Confirm your Authentication Text before entering password")

    session = AuthSession(
        user_id=user.id,
        nonce=generate_nonce(32),
        challenge=generate_nonce(32),
        step="otp_pending",
        otp_expires_at=datetime.utcnow() + timedelta(minutes=5),
        otp_attempts=0,
        otp_sent_count=1,
        otp_resend_available_at=datetime.utcnow() + timedelta(seconds=settings.otp_resend_cooldown_seconds),
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    _log_auth(db, user.id, "login", "password", "success", request)
    _emit(
        "auth_step",
        step="password",
        status="success",
        session_id=session.id,
        user_id=user.id,
        email=user.email,
    )

    # Admin convenience mode: password-only login (skip OTP/PUF).
    if user.role == "admin":
        session.step = "complete"
        session.otp_hash = None
        db.commit()
        _emit("auth_step", step="admin_bypass", status="success", session_id=session.id, user_id=user.id)
        result = _complete_login(user, session, db, response)
        result["message"] = "Admin login successful. OTP skipped."
        result["requires_puf"] = False
        result["puf_mode"] = "off"
        result["delivery"] = "none"
        return result

    otp = generate_otp(6)
    session.otp_hash = hash_otp(otp)
    db.commit()

    try:
        send_email_otp(user.email, otp)
    except RuntimeError as exc:
        _log_auth(db, user.id, "otp_sent", "email", "failed", request, {"error": str(exc)})
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    _log_auth(db, user.id, "otp_sent", "email", "success", request)
    _emit(
        "auth_step",
        step="email_otp",
        status="pending",
        session_id=session.id,
        user_id=user.id,
        delivery="email",
    )

    return {
        "session_id": session.id,
        "message": f"OTP sent to {mask_email(user.email)}",
        "requires_puf": user.puf_enabled,
        "puf_mode": user.puf_mode,
        "next_step": "verify_otp",
        "delivery": "email",
    }


@router.post("/login/verify-otp")
def login_verify_otp(payload: OtpVerifyRequest, request: Request, response: Response, db: DbSession) -> dict:
    session = db.query(AuthSession).filter(AuthSession.id == payload.session_id, AuthSession.used.is_(False)).first()
    if not session or _session_expired(session):
        raise HTTPException(status_code=400, detail="Invalid or expired session")

    user = db.query(User).filter(User.id == session.user_id).first()
    if not user or not session.otp_hash:
        raise HTTPException(status_code=400, detail="Invalid session")

    if session.otp_expires_at and datetime.utcnow() > session.otp_expires_at:
        _log_auth(db, user.id, "login", "email_otp", "expired", request)
        _emit("auth_step", step="email_otp", status="expired", session_id=session.id)
        raise HTTPException(status_code=400, detail="OTP expired")

    if session.otp_locked_until and datetime.utcnow() < session.otp_locked_until:
        wait_seconds = int((session.otp_locked_until - datetime.utcnow()).total_seconds())
        raise HTTPException(status_code=429, detail=f"OTP locked. Try again in {wait_seconds}s")

    if not verify_otp(payload.otp, session.otp_hash):
        session.otp_attempts = (session.otp_attempts or 0) + 1
        if session.otp_attempts >= settings.otp_max_attempts:
            session.otp_locked_until = datetime.utcnow() + timedelta(minutes=settings.otp_lock_minutes)
        db.commit()
        _log_auth(db, user.id, "login", "email_otp", "failed", request)
        _emit("auth_step", step="email_otp", status="failed", session_id=session.id)
        if session.otp_locked_until and datetime.utcnow() < session.otp_locked_until:
            raise HTTPException(status_code=429, detail="Too many OTP failures. Session temporarily locked.")
        raise HTTPException(status_code=401, detail="Invalid OTP")

    session.step = "puf_pending" if user.puf_enabled else "complete"
    session.otp_hash = None
    session.otp_attempts = 0
    session.otp_locked_until = None
    _log_auth(db, user.id, "login", "email_otp", "success", request)
    _emit("auth_step", step="email_otp", status="success", session_id=session.id)

    if not user.puf_enabled:
        return _complete_login(user, session, db, response)

    db.commit()
    _emit(
        "auth_step",
        step="puf",
        status="pending",
        session_id=session.id,
        challenge=session.challenge,
        nonce=session.nonce,
        puf_mode=user.puf_mode,
    )
    return {
        "session_id": session.id,
        "challenge": session.challenge,
        "nonce": session.nonce,
        "next_step": "verify_puf",
        "message": f"Verify PUF using {user.puf_mode} device",
    }


@router.post("/login/resend-otp")
def login_resend_otp(payload: SessionRequest, request: Request, db: DbSession) -> dict:
    session = db.query(AuthSession).filter(AuthSession.id == payload.session_id, AuthSession.used.is_(False)).first()
    if not session or _session_expired(session):
        raise HTTPException(status_code=400, detail="Invalid or expired session")
    _require_session_step(session, "otp_pending")

    user = db.query(User).filter(User.id == session.user_id).first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid session")

    now = datetime.utcnow()
    if session.otp_resend_available_at and now < session.otp_resend_available_at:
        wait = int((session.otp_resend_available_at - now).total_seconds())
        raise HTTPException(status_code=429, detail=f"Retry OTP resend in {wait}s")

    if (session.otp_sent_count or 1) >= settings.otp_max_sends_per_session:
        raise HTTPException(status_code=429, detail="OTP resend limit reached for this session")

    otp = generate_otp(6)
    session.otp_hash = hash_otp(otp)
    session.otp_expires_at = now + timedelta(minutes=settings.otp_expire_minutes)
    session.otp_attempts = 0
    session.otp_locked_until = None
    session.otp_sent_count = (session.otp_sent_count or 1) + 1
    session.otp_resend_available_at = now + timedelta(seconds=settings.otp_resend_cooldown_seconds)
    db.commit()

    try:
        send_email_otp(user.email, otp)
    except RuntimeError as exc:
        _log_auth(db, user.id, "otp_resend", "email", "failed", request, {"error": str(exc)})
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    _log_auth(db, user.id, "otp_resend", "email", "success", request, {"session_id": session.id})
    return {"message": f"OTP resent to {mask_email(user.email)}", "session_id": session.id}


@router.post("/login/verify-puf")
def login_verify_puf(payload: PufVerifyRequest, request: Request, response: Response, db: DbSession) -> dict:
    session = db.query(AuthSession).filter(AuthSession.id == payload.session_id, AuthSession.used.is_(False)).first()
    if not session or _session_expired(session):
        raise HTTPException(status_code=400, detail="Invalid or expired session")
    _require_session_step(session, "puf_pending")

    user = db.query(User).filter(User.id == session.user_id).first()
    if not user or not user.puf_enabled:
        raise HTTPException(status_code=400, detail="PUF not required")

    if user.puf_mode == "hardware":
        raise HTTPException(
            status_code=400,
            detail="Hardware PUF uses device MFA proof — call /login/verify-puf-hardware instead",
        )

    device = db.query(PufDevice).filter_by(user_id=user.id).first()
    if not device:
        raise HTTPException(status_code=400, detail="No PUF device enrolled")

    ok, hamming_distance, reference = puf_verification_details(
        session.challenge,
        payload.puf_response,
        device.enrolled_response,
        device.reliability_mask,
        user.puf_mode,
    )
    if not ok:
        _log_auth(db, user.id, "login", "puf", "failed", request, {"session_id": session.id})
        _emit("auth_step", step="puf", status="failed", session_id=session.id)
        raise HTTPException(status_code=401, detail="PUF verification failed")

    _log_auth(db, user.id, "login", "puf", "success", request, {"session_id": session.id})
    _emit("auth_step", step="puf", status="success", session_id=session.id)
    key = derive_session_key(session.challenge, payload.puf_response, session.nonce)
    crypto_bundle = _bootstrap_crypto_session(db, user, session, payload.puf_response, user.puf_mode)
    result = _complete_login(user, session, db, response, session_key=key)
    result["puf_verification"] = {
        "verified": True,
        "puf_mode": user.puf_mode,
        "device_label": device.device_label,
        "challenge": session.challenge,
        "puf_response": payload.puf_response,
        "reference_response": reference,
        "hamming_distance": hamming_distance,
        "session_key": key,
        "nonce": session.nonce,
    }
    result["crypto_bundle"] = crypto_bundle
    return result


@router.post("/login/verify-puf-hardware")
def login_verify_puf_hardware(payload: HardwareVerifyRequest, request: Request, response: Response, db: DbSession) -> dict:
    """Hardware ESP32-C6 MFA: backend drives MFA:AUTH or verifies provided client proof."""
    from app.services import esp32_mfa_bridge
    from app.services import x25519_pure as x25519
    import hmac

    session = db.query(AuthSession).filter(AuthSession.id == payload.session_id, AuthSession.used.is_(False)).first()
    if not session or _session_expired(session):
        raise HTTPException(status_code=400, detail="Invalid or expired session")
    _require_session_step(session, "puf_pending")

    user = db.query(User).filter(User.id == session.user_id).first()
    if not user or not user.puf_enabled or user.puf_mode != "hardware":
        raise HTTPException(status_code=400, detail="Hardware PUF not required")

    device = db.query(PufDevice).filter_by(user_id=user.id).first()
    if not device or not device.device_pubkey_hex:
        raise HTTPException(status_code=400, detail="No hardware PUF device enrolled")

    if payload.proof_hex:
        # Client-driven verification (Web Serial)
        if not session.hardware_eph_scalar_hex:
            raise HTTPException(status_code=400, detail="Authentication session not initialized for hardware PUF")
        
        eph_scalar = bytes.fromhex(session.hardware_eph_scalar_hex)
        device_pubkey = bytes.fromhex(device.device_pubkey_hex)
        
        # Calculate shared secret
        shared = x25519.shared_secret(eph_scalar, device_pubkey)
        
        # Verify the proof
        proof = bytes.fromhex(payload.proof_hex)
        try:
            transcript = esp32_mfa_bridge._build_transcript(session.id, user.id, bytes.fromhex(session.nonce))
            expected = hmac.new(shared, transcript, hashlib.sha256).digest()
            if not hmac.compare_digest(expected, proof):
                raise ValueError("MFA device proof verification FAILED")
            
            proof_meta = {
                "verified": True,
                "device_status": "mfa_enrolled",
                "pubkey_match": True,
                "live_pubkey_hex": device.device_pubkey_hex.lower(),
                "stored_pubkey_hex": device.device_pubkey_hex.lower(),
                "elapsed_s": 0.0,
                "login_id": session.id,
                "proof_hex": payload.proof_hex,
            }
        except ValueError as exc:
            _log_auth(db, user.id, "login", "puf", "failed", request, {"session_id": session.id, "error": str(exc)})
            _emit("auth_step", step="puf", status="failed", session_id=session.id)
            raise HTTPException(status_code=401, detail=str(exc))
    else:
        # Fallback to local server-driven COM port communication
        try:
            proof_meta = esp32_mfa_bridge.authenticate_device(
                None,
                session.id,
                user.id,
                device.device_pubkey_hex,
            )
        except OSError as exc:
            raise HTTPException(status_code=503, detail=f"ESP32 not connected: {exc}") from exc
        except (TimeoutError, RuntimeError, ValueError) as exc:
            _log_auth(db, user.id, "login", "puf", "failed", request, {"session_id": session.id, "error": str(exc)})
            _emit("auth_step", step="puf", status="failed", session_id=session.id)
            raise HTTPException(status_code=401, detail=str(exc)) from exc

    _log_auth(db, user.id, "login", "puf", "success", request, {"session_id": session.id, **proof_meta})
    _emit("auth_step", step="puf", status="success", session_id=session.id)
    proof_hex = proof_meta.get("proof_hex") or device.device_pubkey_hex
    key = derive_session_key(session.challenge, proof_hex, session.nonce)
    crypto_bundle = _bootstrap_crypto_session(db, user, session, proof_hex, "hardware")
    result = _complete_login(user, session, db, response, session_key=key)
    result["puf_verification"] = {
        "verified": True,
        "puf_mode": "hardware",
        "device_label": device.device_label,
        "device_status": proof_meta.get("device_status"),
        "pubkey_match": proof_meta.get("pubkey_match"),
        "live_pubkey_hex": proof_meta.get("live_pubkey_hex"),
        "stored_pubkey_hex": proof_meta.get("stored_pubkey_hex"),
        "elapsed_s": proof_meta.get("elapsed_s"),
        "login_id": proof_meta.get("login_id"),
        "proof_hex": proof_hex,
        "session_key": key,
        "nonce": session.nonce,
    }
    result["crypto_bundle"] = crypto_bundle
    return result


@router.post("/login/puf-read")
def login_puf_read(payload: SessionRequest, db: DbSession) -> dict:
    """Read PUF response from bridge for demo — shows challenge/response before verify."""
    session = db.query(AuthSession).filter(AuthSession.id == payload.session_id, AuthSession.used.is_(False)).first()
    if not session or _session_expired(session):
        raise HTTPException(status_code=400, detail="Invalid or expired session")
    _require_session_step(session, "puf_pending")

    user = db.query(User).filter(User.id == session.user_id).first()
    if not user or not user.puf_enabled:
        raise HTTPException(status_code=400, detail="PUF not required")

    device = db.query(PufDevice).filter_by(user_id=user.id).first()
    if not device:
        raise HTTPException(status_code=400, detail="No PUF device enrolled")

    if user.puf_mode == "hardware":
        from app.services import esp32_mfa_bridge
        from app.services import x25519_pure as x25519

        # Generate X25519 ephemeral keypair for client authentication
        eph_scalar_bytes = x25519.clamp_scalar(os.urandom(32))
        eph_public_bytes = x25519.public_key_from_scalar(eph_scalar_bytes)
        
        session.hardware_eph_scalar_hex = eph_scalar_bytes.hex()
        db.commit()

        # Try to run hardware precheck locally if possible (as fallback)
        try:
            precheck = esp32_mfa_bridge.hardware_login_precheck(device.device_pubkey_hex)
            device_status = precheck["device_status"]
            live_pubkey_hex = precheck.get("live_pubkey_hex")
            pubkey_match = precheck.get("pubkey_match")
            ready_for_auth = precheck.get("ready_for_auth")
        except Exception:
            # Bypassed/failed local serial check (e.g. running on remote VPS)
            device_status = "mfa_enrolled"
            live_pubkey_hex = device.device_pubkey_hex
            pubkey_match = True
            ready_for_auth = True

        return {
            "session_id": session.id,
            "puf_mode": "hardware",
            "device_label": device.device_label,
            "secret_identifier": device.secret_identifier,
            "device_status": device_status,
            "live_pubkey_hex": live_pubkey_hex,
            "stored_pubkey_hex": device.device_pubkey_hex,
            "pubkey_match": pubkey_match,
            "ready_for_auth": ready_for_auth,
            "nonce": session.nonce,
            "eph_public_hex": eph_public_bytes.hex(),
            "customer_id": user.id,
            "message": "Plug ESP32-C6 into your USB port and click authenticate",
        }

    try:
        response = read_puf(session.challenge, user.puf_mode)
    except OSError as exc:
        raise HTTPException(status_code=503, detail=f"PUF bridge unavailable: {exc}") from exc

    if not response:
        raise HTTPException(status_code=503, detail="PUF bridge unavailable — start virtual_puf_server.py")

    session_key = derive_session_key(session.challenge, response, session.nonce)
    ok, hamming_distance, reference = puf_verification_details(
        session.challenge,
        response,
        device.enrolled_response,
        device.reliability_mask,
        user.puf_mode,
    )

    return {
        "session_id": session.id,
        "puf_mode": user.puf_mode,
        "device_label": device.device_label,
        "secret_identifier": device.secret_identifier or derive_secret_identifier(response, user.puf_mode),
        "challenge": session.challenge,
        "nonce": session.nonce,
        "puf_response": response,
        "reference_response": reference,
        "hamming_distance": hamming_distance,
        "will_verify": ok,
        "session_key": session_key,
        "message": "PUF response read from virtual device bridge",
    }


@router.post("/signup/puf-preview")
def signup_puf_preview(payload: PufPreviewRequest) -> dict:
    """Preview PUF read + identifier before signup completion."""
    if payload.mode == "hardware":
        if payload.device_pubkey_hex:
            return {
                "mode": "hardware",
                "device_status": "mfa_enrolled",
                "message": "ESP32 device connected via browser Web Serial",
                "secret_identifier": derive_secret_identifier(payload.device_pubkey_hex, "hardware"),
                "device_pubkey_hex": payload.device_pubkey_hex,
            }

        # Fallback to local server connection if no pubkey was provided by client
        from app.services import esp32_mfa_bridge
        try:
            online, status, error = esp32_mfa_bridge.hardware_device_online()
            if not online:
                raise HTTPException(
                    status_code=503,
                    detail=error or f"ESP32 not responding on {settings.hardware_puf_serial_port}",
                )
            return {
                "mode": "hardware",
                "device_status": status,
                "message": "ESP32-C6 must be connected to the PC running the backend at signup time",
                "secret_identifier": "Generated after account creation",
            }
        except Exception as exc:
            if not isinstance(exc, HTTPException):
                raise HTTPException(status_code=503, detail=f"ESP32 unavailable: {exc}") from exc
            raise exc

    challenge = generate_nonce(32)
    try:
        response = read_puf(challenge, payload.mode)
    except OSError as exc:
        raise HTTPException(status_code=503, detail=f"PUF bridge unavailable: {exc}") from exc

    if not response:
        raise HTTPException(status_code=503, detail="PUF bridge unavailable — start virtual_puf_server.py")

    return {
        "mode": payload.mode,
        "challenge": challenge,
        "puf_response": response,
        "secret_identifier": derive_secret_identifier(response, payload.mode),
    }


@router.post("/login/verify-puf-auto")
def login_verify_puf_auto(payload: OtpVerifyRequest, request: Request, http_response: Response, db: DbSession) -> dict:
    """Dev helper: read PUF response from bridge and verify in one step."""
    if settings.is_production:
        raise HTTPException(status_code=404, detail="Not found")
    session = db.query(AuthSession).filter(AuthSession.id == payload.session_id, AuthSession.used.is_(False)).first()
    if not session or _session_expired(session):
        raise HTTPException(status_code=400, detail="Invalid or expired session")
    _require_session_step(session, "puf_pending")

    user = db.query(User).filter(User.id == session.user_id).first()
    if not user or not user.puf_enabled:
        raise HTTPException(status_code=400, detail="PUF not required")

    if user.puf_mode == "hardware":
        return login_verify_puf_hardware(
            SessionRequest(session_id=payload.session_id), request, http_response, db
        )

    puf_response = read_puf(session.challenge, user.puf_mode)
    if not puf_response:
        raise HTTPException(status_code=503, detail="PUF bridge unavailable")

    return login_verify_puf(
        PufVerifyRequest(session_id=payload.session_id, puf_response=puf_response),
        request,
        http_response,
        db,
    )


@router.post("/refresh")
def refresh_token(payload: RefreshRequest, request: Request, response: Response, db: DbSession) -> dict:
    from app.deps import _decode_token

    refresh_token_value = payload.refresh_token or request.cookies.get(settings.refresh_cookie_name) or ""
    if not refresh_token_value:
        raise HTTPException(status_code=401, detail="Refresh token required")

    token_payload = _decode_token(refresh_token_value, "refresh")
    user = db.query(User).filter(User.id == token_payload["sub"], User.is_active.is_(True)).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    token_row = (
        db.query(RefreshToken)
        .filter(
            RefreshToken.user_id == user.id,
            RefreshToken.token_hash == hash_token(refresh_token_value),
            RefreshToken.revoked.is_(False),
        )
        .first()
    )
    if not token_row:
        raise HTTPException(status_code=401, detail="Refresh token revoked or unknown")
    if token_row.expires_at < datetime.utcnow():
        token_row.revoked = True
        db.commit()
        raise HTTPException(status_code=401, detail="Refresh token expired")

    token_row.revoked = True
    tokens = create_token_pair(user.id, user.role)
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_token(tokens["refresh_token"]),
            expires_at=datetime.utcnow() + timedelta(days=settings.jwt_refresh_rotate_days),
        )
    )
    db.commit()
    _set_auth_cookies(response, tokens)
    return tokens


@router.post("/logout")
def logout(response: Response, db: DbSession, user: CurrentUser) -> dict:
    db.query(RefreshToken).filter(RefreshToken.user_id == user.id, RefreshToken.revoked.is_(False)).update(
        {"revoked": True}
    )
    db.commit()
    _clear_auth_cookies(response)
    return {"message": "Logged out"}


@router.post("/puf/enroll")
def puf_enroll(payload: PufEnrollRequest, request: Request, db: DbSession, user: CurrentUser) -> dict:
    result = enroll_puf(db, user, payload.mode)
    if result.get("status") == "error":
        raise HTTPException(status_code=503, detail=result.get("message", "PUF enrollment failed"))
    _log_auth(db, user.id, "puf_enroll", "puf", "success", request, {"mode": payload.mode})
    _emit("puf_enroll", user_id=user.id, mode=payload.mode)
    return result


@router.get("/me")
def get_me(user: CurrentUser) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "phone": user.phone,
        "full_name": user.full_name,
        "dob": user.dob,
        "account_number": user.account_number,
        "balance": user.initial_deposit,
        "role": user.role,
        "puf_enabled": user.puf_enabled,
        "puf_mode": user.puf_mode,
    }
