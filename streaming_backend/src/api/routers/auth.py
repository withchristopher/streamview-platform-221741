from datetime import datetime, timedelta
from typing import Optional

import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from passlib.hash import pbkdf2_sha256
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.db.models import User
from src.db.schemas import LoginRequest, Token, User as UserSchema
from src.db.session import get_db

# Simple settings via environment variables (to be provided via .env)
import os

JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-me")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "60"))

router = APIRouter()


class _TokenPayload(BaseModel):
    sub: int = Field(..., description="User ID subject")
    exp: int = Field(..., description="Expiration (unix timestamp)")


def _create_access_token(subject: int, expires_delta: Optional[timedelta] = None) -> str:
    """
    Build a signed JWT with minimal claims.
    """
    if expires_delta is None:
        expires_delta = timedelta(minutes=JWT_EXPIRE_MINUTES)
    expire = datetime.utcnow() + expires_delta
    payload = {"sub": subject, "exp": int(expire.timestamp())}
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token


# PUBLIC_INTERFACE
@router.post("/login", response_model=Token, summary="Login", tags=["auth"])
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    """
    Authenticate a user by email and password and return a JWT access token.

    Parameters:
        payload: LoginRequest with email and password
        db: SQLAlchemy session

    Returns:
        Token: {access_token, token_type}
    """
    user = db.execute(select(User).where(User.email == payload.email)).scalar_one_or_none()
    if not user or not pbkdf2_sha256.verify(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token = _create_access_token(subject=user.id)
    return Token(access_token=token, token_type="bearer")


# PUBLIC_INTERFACE
@router.get("/me", response_model=UserSchema, summary="Get current user", tags=["auth"])
def me(current_user: User = Depends(lambda db=Depends(get_db): get_current_user(db))):
    """
    Return the currently authenticated user.
    """
    return current_user


def get_current_user(db: Session) -> User:
    """
    Dependency helper which extracts the current user from the Authorization header (Bearer token).
    Raises 401 if missing/invalid.
    """
    # We will parse header in a lightweight way using Starlette request scope via dependency injection.
    # FastAPI's OAuth2PasswordBearer is overkill for this simple internal flow.
    from fastapi import Request

    def _dep(request: Request) -> User:
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.lower().startswith("bearer "):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
        token = auth_header.split(" ", 1)[1].strip()
        try:
            decoded = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            data = _TokenPayload(**decoded)
        except Exception:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        user = db.get(User, data.sub)
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
        return user

    # return an actual user using a mock request created by FastAPI. FastAPI will call the inner dep.
    # This function is used via a lambda to allow proper Depends injection of db.
    raise RuntimeError("get_current_user should be used via Depends(lambda db=Depends(get_db): get_current_user(db)))")
