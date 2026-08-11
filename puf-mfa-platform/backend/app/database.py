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
    site_auth_phrase: Mapped[str | None] = mapped_column(String(80), nullable=True)
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
    device_pubkey_hex: Mapped[str | None] = mapped_column(String(64), nullable=True)
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
    hardware_eph_scalar_hex: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class SiteAuthChallenge(Base):
    """Site-to-user authentication phrase shown before password (anti-phishing)."""

    __tablename__ = "site_auth_challenges"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    phrase_shown: Mapped[str] = mapped_column(String(80))
    confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class SessionCryptoState(Base):
    """Ratcheting session keys derived from MFA proof — server holds proof, never the txn key."""

    __tablename__ = "session_crypto_states"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    auth_session_id: Mapped[str] = mapped_column(String(36), unique=True, index=True)
    proof_hex: Mapped[str] = mapped_column(String(128))
    nonce: Mapped[str] = mapped_column(String(64))
    challenge: Mapped[str] = mapped_column(String(64))
    puf_mode: Mapped[str] = mapped_column(String(20), default="hardware")
    ratchet_counter: Mapped[int] = mapped_column(Integer, default=0)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
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
    from app.services.auth_service import hash_password, verify_password

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
            # Keep admin password in sync with ADMIN_PASSWORD env (fixes deploy login drift)
            if settings.admin_password and not verify_password(settings.admin_password, existing.password_hash):
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
    _ensure_schema_columns()
    seed_admin()


def _ensure_schema_columns() -> None:
    """Add missing columns for both SQLite and Postgres (create_all does not alter)."""
    is_sqlite = settings.database_url.startswith("sqlite")
    db = SessionLocal()
    try:
        def cols(table: str) -> set[str]:
            if is_sqlite:
                return {row[1] for row in db.execute(text(f"PRAGMA table_info({table})")).fetchall()}
            rows = db.execute(
                text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_name = :t"
                ),
                {"t": table},
            ).fetchall()
            return {row[0] for row in rows}

        def add(table: str, column: str, ddl: str) -> None:
            if column not in cols(table):
                db.execute(text(f"ALTER TABLE {table} ADD COLUMN {ddl}"))

        add("users", "username", "username VARCHAR(100)")
        add("users", "dob", "dob VARCHAR(20)")
        add("users", "account_number", "account_number VARCHAR(20)")
        add("users", "initial_deposit", "initial_deposit FLOAT DEFAULT 0")
        add("users", "site_auth_phrase", "site_auth_phrase VARCHAR(80)")

        add("puf_devices", "secret_identifier", "secret_identifier VARCHAR(32)")
        add("puf_devices", "device_pubkey_hex", "device_pubkey_hex VARCHAR(64)")

        add("auth_sessions", "otp_attempts", "otp_attempts INTEGER DEFAULT 0")
        add("auth_sessions", "otp_sent_count", "otp_sent_count INTEGER DEFAULT 1")
        add(
            "auth_sessions",
            "otp_locked_until",
            "otp_locked_until TIMESTAMP" if not is_sqlite else "otp_locked_until DATETIME",
        )
        add(
            "auth_sessions",
            "otp_resend_available_at",
            "otp_resend_available_at TIMESTAMP" if not is_sqlite else "otp_resend_available_at DATETIME",
        )
        add("auth_sessions", "hardware_eph_scalar_hex", "hardware_eph_scalar_hex VARCHAR(64)")

        if "site_auth_phrase" in cols("users"):
            db.execute(
                text(
                    "UPDATE users SET site_auth_phrase = 'fine for me' "
                    "WHERE site_auth_phrase IS NULL AND role != 'admin'"
                )
            )

        db.commit()
    finally:
        db.close()
