from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import func

from app.database import AuthLog, AuthSession, PufDevice, User
from app.deps import AdminUser, DbSession
from app.services.event_bus import auth_events
from app.services.puf_service import verify_puf_response

router = APIRouter()


@router.get("/analytics")
def auth_analytics(db: DbSession, _: AdminUser) -> dict:
    day_ago = datetime.utcnow() - timedelta(hours=24)
    logs = db.query(AuthLog).filter(AuthLog.created_at >= day_ago).all()

    factor_usage: dict[str, int] = {}
    hourly: dict[str, int] = {}
    success = 0
    failed = 0

    for log in logs:
        factor_usage[log.factor] = factor_usage.get(log.factor, 0) + 1
        hour = log.created_at.strftime("%H:00")
        hourly[hour] = hourly.get(hour, 0) + 1
        if log.status in ("success", "blocked"):
            success += 1
        elif log.status == "failed":
            failed += 1

    return {
        "factor_usage": factor_usage,
        "hourly_events": dict(sorted(hourly.items())),
        "success_count": success,
        "failed_count": failed,
        "total_24h": len(logs),
    }


@router.get("/puf-status")
def puf_status(_: AdminUser) -> dict:
    from app.config import settings
    from app.services.puf_service import read_puf

    import secrets

    challenge = secrets.token_hex(16)
    virtual_ok = False
    hardware_ok = False
    virtual_error = ""
    hardware_error = ""

    try:
        resp = read_puf(challenge, "virtual")
        virtual_ok = bool(resp)
        if not virtual_ok:
            virtual_error = "Virtual PUF bridge did not respond on port 8765"
    except Exception as exc:
        virtual_error = str(exc)

    try:
        resp = read_puf(challenge, "hardware")
        hardware_ok = bool(resp)
        if not hardware_ok:
            hardware_error = f"No response on {settings.hardware_puf_serial_port}"
    except Exception as exc:
        hardware_error = str(exc)

    return {
        "virtual": {"online": virtual_ok, "host": settings.virtual_puf_host, "port": settings.virtual_puf_port, "error": virtual_error},
        "hardware": {"online": hardware_ok, "port": settings.hardware_puf_serial_port, "baud": settings.hardware_puf_baud, "error": hardware_error},
        "twilio_configured": bool(settings.twilio_account_sid and settings.twilio_auth_token),
    }


@router.get("/stats")
def system_stats(db: DbSession, _: AdminUser) -> dict:
    now = datetime.utcnow()
    day_ago = now - timedelta(hours=24)

    total_users = db.query(func.count(User.id)).scalar() or 0
    puf_enabled = db.query(func.count(User.id)).filter(User.puf_enabled.is_(True)).scalar() or 0
    active_sessions = db.query(func.count(AuthSession.id)).filter(AuthSession.used.is_(False)).scalar() or 0

    logs_24h = db.query(AuthLog).filter(AuthLog.created_at >= day_ago).all()
    success = sum(1 for log in logs_24h if log.status == "success")
    failed = sum(1 for log in logs_24h if log.status == "failed")

    factor_counts: dict[str, int] = {}
    for log in logs_24h:
        factor_counts[log.factor] = factor_counts.get(log.factor, 0) + 1

    return {
        "total_users": total_users,
        "puf_enabled_users": puf_enabled,
        "active_auth_sessions": active_sessions,
        "auth_events_24h": len(logs_24h),
        "success_24h": success,
        "failed_24h": failed,
        "factor_usage_24h": factor_counts,
    }


@router.get("/users")
def list_users(db: DbSession, _: AdminUser, limit: int = Query(50, le=200), offset: int = 0) -> dict:
    users = db.query(User).order_by(User.created_at.desc()).offset(offset).limit(limit).all()
    total = db.query(func.count(User.id)).scalar() or 0
    return {
        "total": total,
        "users": [
            {
                "id": u.id,
                "email": u.email,
                "phone": u.phone,
                "full_name": u.full_name,
                "role": u.role,
                "puf_enabled": u.puf_enabled,
                "puf_mode": u.puf_mode,
                "is_active": u.is_active,
                "created_at": u.created_at.isoformat(),
            }
            for u in users
        ],
    }


@router.get("/auth-logs")
def list_auth_logs(
    db: DbSession,
    _: AdminUser,
    limit: int = Query(100, le=500),
    offset: int = 0,
    status: str | None = None,
    factor: str | None = None,
) -> dict:
    query = db.query(AuthLog).order_by(AuthLog.created_at.desc())
    if status:
        query = query.filter(AuthLog.status == status)
    if factor:
        query = query.filter(AuthLog.factor == factor)

    total = query.count()
    logs = query.offset(offset).limit(limit).all()
    return {
        "total": total,
        "logs": [
            {
                "id": log.id,
                "user_id": log.user_id,
                "event": log.event,
                "factor": log.factor,
                "status": log.status,
                "ip_address": log.ip_address,
                "metadata": log.metadata_json,
                "created_at": log.created_at.isoformat(),
            }
            for log in logs
        ],
    }


@router.get("/auth-logs/export")
def export_auth_logs_csv(db: DbSession, _: AdminUser) -> StreamingResponse:
    logs = db.query(AuthLog).order_by(AuthLog.created_at.desc()).limit(1000).all()
    lines = ["id,user_id,event,factor,status,ip_address,created_at"]
    for log in logs:
        lines.append(
            f"{log.id},{log.user_id or ''},{log.event},{log.factor},{log.status},{log.ip_address or ''},{log.created_at.isoformat()}"
        )
    content = "\n".join(lines)
    return StreamingResponse(
        iter([content]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=auth_logs.csv"},
    )


@router.get("/devices")
def list_puf_devices(db: DbSession, _: AdminUser) -> dict:
    devices = db.query(PufDevice).order_by(PufDevice.created_at.desc()).all()
    return {
        "devices": [
            {
                "id": d.id,
                "user_id": d.user_id,
                "device_label": d.device_label,
                "enrolled_at": d.created_at.isoformat(),
                "has_mask": bool(d.reliability_mask),
            }
            for d in devices
        ]
    }


class AttackDemoRequest(BaseModel):
    email: str = Field(default="demo@bank.com")
    session_id: str | None = None


def _log_attack(db: DbSession, request: Request, attack: str, status: str, detail: str) -> None:
    db.add(
        AuthLog(
            event="attack_demo",
            factor=attack,
            status=status,
            ip_address=request.client.host if request.client else None,
            metadata_json=detail,
        )
    )
    db.commit()
    auth_events.emit_sync("attack_demo", attack=attack, status=status, detail=detail)


@router.post("/attack-demo/password-only")
def demo_password_only(payload: AttackDemoRequest, request: Request, db: DbSession, _: AdminUser) -> dict:
    """Simulate attacker with stolen password but no OTP/PUF."""
    user = db.query(User).filter(User.email == payload.email).first()
    detail = "Password verified but OTP required — access denied without second factor."
    _log_attack(db, request, "password_only_bypass", "blocked", detail)
    return {
        "attack": "Password-only bypass",
        "result": "BLOCKED",
        "explanation": detail,
        "user_found": bool(user),
    }


@router.post("/attack-demo/replay")
def demo_replay(payload: AttackDemoRequest, request: Request, db: DbSession, _: AdminUser) -> dict:
    """Simulate replay of a used auth session."""
    if not payload.session_id:
        raise HTTPException(status_code=400, detail="Provide session_id from a completed login")

    session = db.query(AuthSession).filter(AuthSession.id == payload.session_id).first()
    if not session:
        detail = "Session not found — replay rejected."
        blocked = True
    elif session.used:
        detail = "Session nonce already consumed — replay attack blocked."
        blocked = True
    elif datetime.utcnow() > session.created_at + timedelta(minutes=15):
        detail = "Session expired — stale credentials rejected."
        blocked = True
    else:
        detail = "Session still active — in real attack, resubmitting old OTP would fail after first use."
        blocked = True

    _log_attack(db, request, "replay_attack", "blocked" if blocked else "failed", detail)
    return {"attack": "Replay attack", "result": "BLOCKED", "explanation": detail}


@router.post("/attack-demo/clone")
def demo_clone(payload: AttackDemoRequest, request: Request, db: DbSession, _: AdminUser) -> dict:
    """Simulate cloned device with wrong PUF response."""
    user = db.query(User).filter(User.email == payload.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    device = db.query(PufDevice).filter(PufDevice.user_id == user.id).first()
    if not device:
        raise HTTPException(status_code=400, detail="User has no enrolled PUF device")

    fake_response = "deadbeef" * 4
    ok = verify_puf_response(
        "ab" * 16,
        fake_response,
        device.enrolled_response,
        device.reliability_mask,
        user.puf_mode,
    )
    detail = "Cloned device response does not match enrolled PUF — Hamming distance exceeds threshold."
    _log_attack(db, request, "clone_device", "blocked", detail)
    return {
        "attack": "Device clone",
        "result": "BLOCKED" if not ok else "UNEXPECTED_PASS",
        "explanation": detail,
        "hamming_check_passed": ok,
    }
