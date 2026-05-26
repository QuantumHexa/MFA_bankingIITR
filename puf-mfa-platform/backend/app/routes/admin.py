from datetime import datetime, timedelta

from fastapi import APIRouter, Query
from sqlalchemy import func

from app.database import AuthLog, AuthSession, PufDevice, User
from app.deps import AdminUser, DbSession

router = APIRouter()


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
