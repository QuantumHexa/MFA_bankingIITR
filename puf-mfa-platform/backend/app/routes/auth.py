from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app.database import AuthLog, AuthSession, PufDevice, User
from app.config import settings
from app.deps import CurrentUser, DbSession
from app.services.auth_service import (
    create_token_pair,
    generate_nonce,
    hash_password,
    verify_password,
)
from app.services.event_bus import auth_events
from app.services.otp_service import generate_otp, hash_otp, send_whatsapp_otp, verify_otp
from app.services.puf_service import enroll_puf, derive_session_key, read_puf, verify_puf_response

router = APIRouter()

SESSION_TTL_MINUTES = 15


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


def _complete_login(user: User, session: AuthSession, db: Session, session_key: str | None = None) -> dict:
    session.used = True
    db.commit()
    tokens = create_token_pair(user.id, user.role)
    _emit("auth_complete", user_id=user.id, email=user.email, role=user.role)
    result = {**tokens, "next_step": "dashboard"}
    if session_key:
        result["session_key_preview"] = session_key[:16] + "..."
    return result


class SignupRequest(BaseModel):
    email: EmailStr
    phone: str = Field(..., pattern=r"^\d{10}$")
    full_name: str = Field(..., min_length=2, max_length=100)
    password: str = Field(..., min_length=8)
    puf_enabled: bool = False
    puf_mode: str = Field(default="virtual", pattern=r"^(virtual|hardware|off)$")


class LoginStartRequest(BaseModel):
    email: EmailStr
    password: str


class OtpVerifyRequest(BaseModel):
    session_id: str
    otp: str = Field(..., min_length=6, max_length=6)


class PufVerifyRequest(BaseModel):
    session_id: str
    puf_response: str = Field(..., min_length=32, max_length=32)


class RefreshRequest(BaseModel):
    refresh_token: str


class PufEnrollRequest(BaseModel):
    mode: str = Field(default="virtual", pattern=r"^(virtual|hardware)$")


@router.post("/signup")
def signup(payload: SignupRequest, request: Request, db: DbSession) -> dict:
    if db.query(User).filter((User.email == payload.email) | (User.phone == payload.phone)).first():
        raise HTTPException(status_code=400, detail="Email or phone already registered")

    user = User(
        email=payload.email,
        phone=payload.phone,
        full_name=payload.full_name,
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
        "puf_enabled": user.puf_enabled,
        "puf_enrollment": enroll_result,
    }


@router.post("/login/start")
def login_start(payload: LoginStartRequest, request: Request, db: DbSession) -> dict:
    user = db.query(User).filter(User.email == payload.email, User.is_active.is_(True)).first()
    if not user or not verify_password(payload.password, user.password_hash):
        _log_auth(db, user.id if user else None, "login", "password", "failed", request)
        _emit("auth_step", step="password", status="failed", email=payload.email)
        raise HTTPException(status_code=401, detail="Invalid credentials")

    session = AuthSession(
        user_id=user.id,
        nonce=generate_nonce(32),
        challenge=generate_nonce(32),
        step="otp_pending",
        otp_expires_at=datetime.utcnow() + timedelta(minutes=5),
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    otp = generate_otp(6)
    session.otp_hash = hash_otp(otp)
    db.commit()

    sent = send_whatsapp_otp(user.phone, otp)
    _log_auth(db, user.id, "login", "password", "success", request)
    _log_auth(db, user.id, "otp_sent", "whatsapp", "success" if sent else "simulated", request)
    _emit(
        "auth_step",
        step="password",
        status="success",
        session_id=session.id,
        user_id=user.id,
        email=user.email,
    )
    _emit(
        "auth_step",
        step="whatsapp_otp",
        status="pending",
        session_id=session.id,
        user_id=user.id,
        delivery="whatsapp" if sent else "dev_console",
    )

    response = {
        "session_id": session.id,
        "message": "WhatsApp OTP sent" if sent else "OTP generated (dev mode)",
        "requires_puf": user.puf_enabled,
        "puf_mode": user.puf_mode,
        "next_step": "verify_otp",
        "delivery": "whatsapp" if sent else "dev",
    }
    if not sent and settings.app_env == "development":
        response["dev_otp"] = otp
    return response


@router.post("/login/verify-otp")
def login_verify_otp(payload: OtpVerifyRequest, request: Request, db: DbSession) -> dict:
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

    if not verify_otp(payload.otp, session.otp_hash):
        _log_auth(db, user.id, "login", "whatsapp_otp", "failed", request)
        _emit("auth_step", step="whatsapp_otp", status="failed", session_id=session.id)
        raise HTTPException(status_code=401, detail="Invalid OTP")

    session.step = "puf_pending" if user.puf_enabled else "complete"
    session.otp_hash = None
    _log_auth(db, user.id, "login", "whatsapp_otp", "success", request)
    _emit("auth_step", step="whatsapp_otp", status="success", session_id=session.id)

    if not user.puf_enabled:
        return _complete_login(user, session, db)

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


@router.post("/login/verify-puf")
def login_verify_puf(payload: PufVerifyRequest, request: Request, db: DbSession) -> dict:
    session = db.query(AuthSession).filter(AuthSession.id == payload.session_id, AuthSession.used.is_(False)).first()
    if not session or _session_expired(session):
        raise HTTPException(status_code=400, detail="Invalid or expired session")

    user = db.query(User).filter(User.id == session.user_id).first()
    if not user or not user.puf_enabled:
        raise HTTPException(status_code=400, detail="PUF not required")

    device = db.query(PufDevice).filter_by(user_id=user.id).first()
    if not device:
        raise HTTPException(status_code=400, detail="No PUF device enrolled")

    ok = verify_puf_response(
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
    return _complete_login(user, session, db, session_key=key)


@router.post("/login/verify-puf-auto")
def login_verify_puf_auto(payload: OtpVerifyRequest, request: Request, db: DbSession) -> dict:
    """Dev helper: read PUF response from bridge and verify in one step."""
    session = db.query(AuthSession).filter(AuthSession.id == payload.session_id, AuthSession.used.is_(False)).first()
    if not session or _session_expired(session):
        raise HTTPException(status_code=400, detail="Invalid or expired session")

    user = db.query(User).filter(User.id == session.user_id).first()
    if not user or not user.puf_enabled:
        raise HTTPException(status_code=400, detail="PUF not required")

    response = read_puf(session.challenge, user.puf_mode)
    if not response:
        raise HTTPException(status_code=503, detail="PUF bridge unavailable")

    return login_verify_puf(
        PufVerifyRequest(session_id=payload.session_id, puf_response=response),
        request,
        db,
    )


@router.post("/refresh")
def refresh_token(payload: RefreshRequest, db: DbSession) -> dict:
    from app.deps import _decode_token

    token_payload = _decode_token(payload.refresh_token, "refresh")
    user = db.query(User).filter(User.id == token_payload["sub"], User.is_active.is_(True)).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return create_token_pair(user.id, user.role)


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
        "email": user.email,
        "phone": user.phone,
        "full_name": user.full_name,
        "role": user.role,
        "puf_enabled": user.puf_enabled,
        "puf_mode": user.puf_mode,
    }
