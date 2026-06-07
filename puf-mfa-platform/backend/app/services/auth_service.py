import secrets
from hashlib import sha256
from datetime import datetime, timedelta

import bcrypt
from jose import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.config import settings

ALGORITHM = "HS256"
_argon = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=2)


def _pepper(value: str) -> str:
    return f"{value}{settings.password_pepper or ''}"


def hash_password(password: str) -> str:
    peppered = _pepper(password)
    return _argon.hash(peppered)


def verify_password(plain: str, hashed: str) -> bool:
    peppered = _pepper(plain)
    if hashed.startswith("$argon2"):
        try:
            _argon.verify(hashed, peppered)
            return True
        except VerifyMismatchError:
            return False
    # backward compatibility for legacy bcrypt hashes
    return bcrypt.checkpw(peppered.encode(), hashed.encode())


def create_access_token(user_id: str, role: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=settings.jwt_access_token_expire_minutes)
    payload = {"sub": user_id, "role": role, "exp": expire, "type": "access"}
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def create_refresh_token(user_id: str, role: str) -> str:
    expire = datetime.utcnow() + timedelta(days=settings.jwt_refresh_token_expire_days)
    payload = {"sub": user_id, "role": role, "exp": expire, "type": "refresh", "jti": generate_nonce(32)}
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def create_token_pair(user_id: str, role: str) -> dict[str, str]:
    return {
        "access_token": create_access_token(user_id, role),
        "refresh_token": create_refresh_token(user_id, role),
        "token_type": "bearer",
    }


def generate_nonce(length: int = 32) -> str:
    return secrets.token_hex(length // 2)


def hash_token(token: str) -> str:
    return sha256(token.encode()).hexdigest()
