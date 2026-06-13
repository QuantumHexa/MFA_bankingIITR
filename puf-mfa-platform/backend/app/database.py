import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, create_engine, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker

from app.config import settings


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username: Mapped[str | None] = mapped_column(String(100), unique=True, index=True, nullable=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    phone: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255))
    dob: Mapped[str | None] = mapped_column(String(20), nullable=True)
    account_number: Mapped[str | None] = mapped_column(String(20), unique=True, index=True, nullable=True)
    initial_deposit: Mapped[float] = mapped_column(Float, default=0.0)
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
    secret_identifier: Mapped[str | None] = mapped_column(String(32), nullable=True)
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
    otp_attempts: Mapped[int] = mapped_column(Integer, default=0)
    otp_sent_count: Mapped[int] = mapped_column(Integer, default=1)
    otp_locked_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    otp_resend_available_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    step: Mapped[str] = mapped_column(String(30), default="password_pending")
    used: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)
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
            updated = False
            if existing.email != settings.admin_email:
                existing.email = settings.admin_email
                updated = True
            if not existing.username:
                existing.username = "admin"
                updated = True
            if not existing.account_number:
                existing.account_number = "100000000001"
                updated = True
            if existing.dob is None:
                existing.dob = "1990-01-01"
                updated = True
            # Keep admin password aligned with configured ADMIN_PASSWORD.
            existing.password_hash = hash_password(settings.admin_password)
            updated = True
            if updated:
                db.commit()
            return
        admin = User(
            username="admin",
            email=settings.admin_email,
            phone="9999999999",
            full_name="Platform Admin",
            dob="1990-01-01",
            account_number="100000000001",
            initial_deposit=0.0,
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
    if settings.database_url.startswith("sqlite"):
        _ensure_sqlite_columns()
    seed_admin()


def _ensure_sqlite_columns() -> None:
    db = SessionLocal()
    try:
        user_cols = {row[1] for row in db.execute(text("PRAGMA table_info(users)")).fetchall()}
        if "username" not in user_cols:
            db.execute(text("ALTER TABLE users ADD COLUMN username VARCHAR(100)"))
        if "dob" not in user_cols:
            db.execute(text("ALTER TABLE users ADD COLUMN dob VARCHAR(20)"))
        if "account_number" not in user_cols:
            db.execute(text("ALTER TABLE users ADD COLUMN account_number VARCHAR(20)"))
        if "initial_deposit" not in user_cols:
            db.execute(text("ALTER TABLE users ADD COLUMN initial_deposit FLOAT DEFAULT 0"))

        puf_cols = {row[1] for row in db.execute(text("PRAGMA table_info(puf_devices)")).fetchall()}
        if "secret_identifier" not in puf_cols:
            db.execute(text("ALTER TABLE puf_devices ADD COLUMN secret_identifier VARCHAR(32)"))

        auth_session_cols = {row[1] for row in db.execute(text("PRAGMA table_info(auth_sessions)")).fetchall()}
        if "otp_attempts" not in auth_session_cols:
            db.execute(text("ALTER TABLE auth_sessions ADD COLUMN otp_attempts INTEGER DEFAULT 0"))
        if "otp_sent_count" not in auth_session_cols:
            db.execute(text("ALTER TABLE auth_sessions ADD COLUMN otp_sent_count INTEGER DEFAULT 1"))
        if "otp_locked_until" not in auth_session_cols:
            db.execute(text("ALTER TABLE auth_sessions ADD COLUMN otp_locked_until DATETIME"))
        if "otp_resend_available_at" not in auth_session_cols:
            db.execute(text("ALTER TABLE auth_sessions ADD COLUMN otp_resend_available_at DATETIME"))

        db.commit()
    finally:
        db.close()
