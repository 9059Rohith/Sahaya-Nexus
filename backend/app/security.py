from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from .config import settings
from .database import get_db
from .models import RevokedToken, User

hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return hasher.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    try:
        return hasher.verify(hashed, password)
    except (VerifyMismatchError, ValueError):
        return False


def token_for(user: User) -> str:
    return jwt.encode(
        {"sub": user.id, "jti": str(uuid4()), "exp": datetime.now(timezone.utc) + timedelta(hours=12)},
        settings.secret_key,
        algorithm="HS256",
    )


def current_user(request: Request, db: Session = Depends(get_db)) -> User:
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Authentication required")
    try:
        payload = jwt.decode(header[7:], settings.secret_key, algorithms=["HS256"])
        user = db.get(User, payload["sub"])
        revoked = db.get(RevokedToken, payload["jti"])
    except (jwt.PyJWTError, KeyError):
        user = None
        revoked = None
    if not user or revoked or user.role in {"DELETED", "SYSTEM"}:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid session")
    return user


def staff(user: User = Depends(current_user)) -> User:
    if user.role not in {"OPERATOR", "ADMIN"}:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Staff access required")
    return user
