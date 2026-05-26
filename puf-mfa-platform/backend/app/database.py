import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker

from app.config import settings


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    phone: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255))
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default="user")
    puf_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    puf_mode: Mapped[str] = mapped_column(String(20), default="virtual")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    devices: Mapped[list["PufDevice"]] = relationship(back_populates="user")
    auth_logs: Mapped[list["AuthLog"]] = relationship(back_populates="user")


class PufDevice(Base):
    __tablename__ = "puf_devices"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    device_label: Mapped[str] = mapped_column(String(100), default="Primary Device")
    enrolled_response: Mapped[str] = mapped_column(Text)
    reliability_mask: Mapped[str | None] = mapped_column(Text, nullable=True)
    challenge_seed: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship(back_populates="devices")


class AuthSession(Base):
    __tablename__ = "auth_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    nonce: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    challenge: Mapped[str] = mapped_column(String(64))
    otp_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    otp_expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    step: Mapped[str] = mapped_column(String(30), default="password_pending")
    used: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AuthLog(Base):
    __tablename__ = "auth_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    event: Mapped[str] = mapped_column(String(50))
    factor: Mapped[str] = mapped_column(String(30))
    status: Mapped[str] = mapped_column(String(20))
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User | None"] = relationship(back_populates="auth_logs")


engine = create_engine(settings.database_url, connect_args={"check_same_thread": False} if settings.database_url.startswith("sqlite") else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def seed_admin() -> None:
    from app.config import settings
    from app.services.auth_service import hash_password

    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.role == "admin").first()
        if existing:
            if existing.email != settings.admin_email:
                existing.email = settings.admin_email
                db.commit()
            return
        admin = User(
            email=settings.admin_email,
            phone="9999999999",
            full_name="Platform Admin",
            password_hash=hash_password(settings.admin_password),
            role="admin",
            puf_enabled=False,
            puf_mode="off",
        )
        db.add(admin)
        db.commit()
    finally:
        db.close()


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    seed_admin()
