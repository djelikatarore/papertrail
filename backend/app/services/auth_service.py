"""
PaperTrail — Password hashing utility (Sprint 2, Task 10)
"""
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.config.settings import JWT_SECRET_KEY, JWT_ALGORITHM, JWT_EXPIRE_MINUTES


def hash_password(plain_password: str) -> str:
    """Hash a plain-text password before storing it in the database."""
    password_bytes = plain_password.encode("utf-8")
    hashed = bcrypt.hashpw(password_bytes, bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Check a plain-text password against a stored hash."""
    password_bytes = plain_password.encode("utf-8")
    hashed_bytes = hashed_password.encode("utf-8")
    return bcrypt.checkpw(password_bytes, hashed_bytes)


def create_access_token(user_id: int) -> tuple[str, datetime]:
    """Create a signed JWT for a user, returning the token and its expiry."""
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=JWT_EXPIRE_MINUTES)
    payload = {"sub": str(user_id), "exp": expires_at}
    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return token, expires_at