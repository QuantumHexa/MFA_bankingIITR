from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.database import User
from app.deps import CurrentUser, DbSession
from app.services.puf_service import enroll_puf

router = APIRouter()


class PufToggleRequest(BaseModel):
    puf_enabled: bool
    puf_mode: str = Field(default="virtual", pattern=r"^(virtual|hardware|off)$")
    device_pubkey_hex: str | None = None


@router.patch("/puf-settings")
def update_puf_settings(payload: PufToggleRequest, db: DbSession, user: CurrentUser) -> dict:
    user.puf_enabled = payload.puf_enabled and payload.puf_mode != "off"
    user.puf_mode = "off" if not payload.puf_enabled else payload.puf_mode
    db.commit()

    enroll_result = None
    if user.puf_enabled:
        enroll_result = enroll_puf(db, user, user.puf_mode, payload.device_pubkey_hex)

    return {
        "user_id": user.id,
        "puf_enabled": user.puf_enabled,
        "puf_mode": user.puf_mode,
        "puf_enrollment": enroll_result,
        "message": "PUF settings updated",
    }


@router.get("/profile")
def get_profile(user: CurrentUser) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "phone": user.phone,
        "full_name": user.full_name,
        "dob": user.dob,
        "account_number": user.account_number,
        "balance": user.initial_deposit,
        "puf_enabled": user.puf_enabled,
        "puf_mode": user.puf_mode,
        "role": user.role,
    }


@router.get("/auth-history")
def get_auth_history(db: DbSession, user: CurrentUser, limit: int = 20) -> dict:
    from app.database import AuthLog

    logs = (
        db.query(AuthLog)
        .filter(AuthLog.user_id == user.id)
        .order_by(AuthLog.created_at.desc())
        .limit(limit)
        .all()
    )
    return {
        "logs": [
            {
                "event": log.event,
                "factor": log.factor,
                "status": log.status,
                "ip_address": log.ip_address,
                "created_at": log.created_at.isoformat(),
            }
            for log in logs
        ]
    }
