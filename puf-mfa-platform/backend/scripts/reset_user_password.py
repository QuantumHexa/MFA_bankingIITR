"""Reset a user's password by username or email (Render Shell / local).

Usage:
  python -m scripts.reset_user_password --user rohit --password 'NewPass123'
"""

from __future__ import annotations

import argparse

from app.database import SessionLocal, User, init_db
from app.services.auth_service import hash_password


def main() -> None:
    parser = argparse.ArgumentParser(description="Reset a user password")
    parser.add_argument("--user", required=True, help="Username or email")
    parser.add_argument("--password", required=True, help="New password (min 8 chars)")
    args = parser.parse_args()

    if len(args.password) < 8:
        raise SystemExit("Password must be at least 8 characters")

    init_db()
    db = SessionLocal()
    try:
        user = (
            db.query(User)
            .filter((User.username == args.user) | (User.email == args.user))
            .first()
        )
        if not user:
            raise SystemExit(f"User not found: {args.user}")
        user.password_hash = hash_password(args.password)
        db.commit()
        print(f"Password updated for {user.username or user.email} ({user.role})")
    finally:
        db.close()


if __name__ == "__main__":
    main()
