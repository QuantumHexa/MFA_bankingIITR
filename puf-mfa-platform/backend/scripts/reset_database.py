"""Reset platform database — keeps only seeded admin account."""

from pathlib import Path

from app.config import settings
from app.database import (
    AuthLog,
    AuthSession,
    PufDevice,
    RefreshToken,
    SessionCryptoState,
    SessionLocal,
    SiteAuthChallenge,
    User,
    init_db,
)


def _wipe_tables() -> None:
    db = SessionLocal()
    try:
        db.query(AuthLog).delete()
        db.query(RefreshToken).delete()
        db.query(SessionCryptoState).delete()
        db.query(SiteAuthChallenge).delete()
        db.query(PufDevice).delete()
        db.query(AuthSession).delete()
        db.query(User).delete()
        db.commit()
    finally:
        db.close()
    init_db()
    print("All user data wiped; admin re-seeded.")


def reset_database() -> None:
    if not settings.database_url.startswith("sqlite"):
        raise SystemExit("reset_database.py only supports SQLite (delete file manually for Postgres).")

    db_path = settings.database_url.replace("sqlite:///", "")
    path = Path(db_path)
    if not path.is_absolute():
        path = Path(__file__).resolve().parents[1] / db_path

    if path.exists():
        try:
            path.unlink()
            init_db()
            print(f"Deleted {path} and recreated schema.")
            return
        except OSError:
            print("Database file locked — wiping tables in place...")
            _wipe_tables()
            return

    init_db()
    print("Database created with admin account only.")


if __name__ == "__main__":
    reset_database()
