import hashlib
import random
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app.config import settings
from app.database import AuthLog, AuthSession, PufDevice, RefreshToken, User
from app.deps import CurrentUser, DbSession
from app.services.auth_service import (
    create_token_pair,
    generate_nonce,
    hash_token,
    hash_password,
    verify_password,
)
from app.services.event_bus import auth_events
from app.services.otp_service import generate_otp, hash_otp, send_whatsapp_otp, verify_otp
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


class SignupRequest(BaseModel):
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


class LoginStartRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=100)
    password: str


class OtpVerifyRequest(BaseModel):
    session_id: str
    otp: str = Field(..., min_length=6, max_length=6)


class SessionRequest(BaseModel):
    session_id: str


class PufVerifyRequest(BaseModel):
    session_id: str
    puf_response: str = Field(..., min_length=32, max_length=32)


class RefreshRequest(BaseModel):
    refresh_token: str | None = None


class PufEnrollRequest(BaseModel):
    mode: str = Field(default="virtual", pattern=r"^(virtual|hardware)$")


class PufPreviewRequest(BaseModel):
    mode: str = Field(default="virtual", pattern=r"^(virtual|hardware)$")


def _generate_account_number(payload: SignupRequest) -> str:
    # Blend user profile fields + randomness into a 12-digit account number.
    raw = (
        f"{payload.full_name}|{payload.dob}|{payload.phone}|"
        f"{payload.email}|{payload.username}|{payload.puf_mode}|{random.random()}"
    )
    digest = hashlib.sha256(raw.encode()).hexdigest()
    digits = str(int(digest[:12], 16))
    return digits[:12].rjust(12, "0")


@router.post("/signup")
def signup(payload: SignupRequest, request: Request, db: DbSession) -> dict:
    if db.query(User).filter(
        (User.email == payload.email) | (User.phone == payload.phone) | (User.username == payload.username)
    ).first():
        raise HTTPException(status_code=400, detail="Email, phone, or username already registered")

    if not payload.netbanking_enabled:
        raise HTTPException(status_code=400, detail="Netbanking must be enabled for this platform")

    account_number = _generate_account_number(payload)
    while db.query(User).filter(User.account_number == account_number).first():
        account_number = _generate_account_number(payload)

    user = User(
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
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    enroll_result = None
    if user.puf_enabled:
        enroll_result = enroll_puf(db, user, user.puf_mode)

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
        send_whatsapp_otp(user.phone, otp)
    except RuntimeError as exc:
        _log_auth(db, user.id, "otp_sent", "whatsapp", "failed", request, {"error": str(exc)})
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    _log_auth(db, user.id, "otp_sent", "whatsapp", "success", request)
    _emit(
        "auth_step",
        step="whatsapp_otp",
        status="pending",
        session_id=session.id,
        user_id=user.id,
        delivery="whatsapp",
    )

    return {
        "session_id": session.id,
        "message": f"OTP sent to WhatsApp ending in {user.phone[-4:]}",
        "requires_puf": user.puf_enabled,
        "puf_mode": user.puf_mode,
        "next_step": "verify_otp",
        "delivery": "whatsapp",
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
        _log_auth(db, user.id, "login", "whatsapp_otp", "expired", request)
        _emit("auth_step", step="whatsapp_otp", status="expired", session_id=session.id)
        raise HTTPException(status_code=400, detail="OTP expired")

    if session.otp_locked_until and datetime.utcnow() < session.otp_locked_until:
        wait_seconds = int((session.otp_locked_until - datetime.utcnow()).total_seconds())
        raise HTTPException(status_code=429, detail=f"OTP locked. Try again in {wait_seconds}s")

    if not verify_otp(payload.otp, session.otp_hash):
        session.otp_attempts = (session.otp_attempts or 0) + 1
        if session.otp_attempts >= settings.otp_max_attempts:
            session.otp_locked_until = datetime.utcnow() + timedelta(minutes=settings.otp_lock_minutes)
        db.commit()
        _log_auth(db, user.id, "login", "whatsapp_otp", "failed", request)
        _emit("auth_step", step="whatsapp_otp", status="failed", session_id=session.id)
        if session.otp_locked_until and datetime.utcnow() < session.otp_locked_until:
            raise HTTPException(status_code=429, detail="Too many OTP failures. Session temporarily locked.")
        raise HTTPException(status_code=401, detail="Invalid OTP")

    session.step = "puf_pending" if user.puf_enabled else "complete"
    session.otp_hash = None
    session.otp_attempts = 0
    session.otp_locked_until = None
    _log_auth(db, user.id, "login", "whatsapp_otp", "success", request)
    _emit("auth_step", step="whatsapp_otp", status="success", session_id=session.id)

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
        send_whatsapp_otp(user.phone, otp)
    except RuntimeError as exc:
        _log_auth(db, user.id, "otp_resend", "whatsapp", "failed", request, {"error": str(exc)})
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    _log_auth(db, user.id, "otp_resend", "whatsapp", "success", request, {"session_id": session.id})
    return {"message": f"OTP resent to WhatsApp ending in {user.phone[-4:]}", "session_id": session.id}


@router.post("/login/verify-puf")
def login_verify_puf(payload: PufVerifyRequest, request: Request, response: Response, db: DbSession) -> dict:
    session = db.query(AuthSession).filter(AuthSession.id == payload.session_id, AuthSession.used.is_(False)).first()
    if not session or _session_expired(session):
        raise HTTPException(status_code=400, detail="Invalid or expired session")

    user = db.query(User).filter(User.id == session.user_id).first()
    if not user or not user.puf_enabled:
        raise HTTPException(status_code=400, detail="PUF not required")

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
    return result


@router.post("/login/puf-read")
def login_puf_read(payload: OtpVerifyRequest, db: DbSession) -> dict:
    """Read PUF response from bridge for demo — shows challenge/response before verify."""
    session = db.query(AuthSession).filter(AuthSession.id == payload.session_id, AuthSession.used.is_(False)).first()
    if not session or _session_expired(session):
        raise HTTPException(status_code=400, detail="Invalid or expired session")

    user = db.query(User).filter(User.id == session.user_id).first()
    if not user or not user.puf_enabled:
        raise HTTPException(status_code=400, detail="PUF not required")

    device = db.query(PufDevice).filter_by(user_id=user.id).first()
    if not device:
        raise HTTPException(status_code=400, detail="No PUF device enrolled")

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
    session = db.query(AuthSession).filter(AuthSession.id == payload.session_id, AuthSession.used.is_(False)).first()
    if not session or _session_expired(session):
        raise HTTPException(status_code=400, detail="Invalid or expired session")

    user = db.query(User).filter(User.id == session.user_id).first()
    if not user or not user.puf_enabled:
        raise HTTPException(status_code=400, detail="PUF not required")

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
