from datetime import datetime, timedelta
from typing import Optional

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, status
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
    """Internal representation of JWT payload used for auth."""
    sub: int = Field(..., description="User ID subject")
    exp: int = Field(..., description="Expiration (unix timestamp)")


def _create_access_token(subject: int, expires_delta: Optional[timedelta] = None) -> str:
    """
    Build a signed JWT with minimal claims.

    Args:
        subject: User ID that will be stored as `sub` in the token.
        expires_delta: Optional timedelta for token lifetime. If omitted,
            JWT_EXPIRE_MINUTES from environment is used.

    Returns:
        str: Encoded JWT token string.
    """
    if expires_delta is None:
        expires_delta = timedelta(minutes=JWT_EXPIRE_MINUTES)
    expire = datetime.utcnow() + expires_delta
    payload = {"sub": subject, "exp": int(expire.timestamp())}
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token


# PUBLIC_INTERFACE
@router.post(
    "/signup",
    response_model=Token,
    summary="Sign up",
    description="Create a new user account with a unique email and return a JWT access token.",
    tags=["auth"],
)
def signup(payload: LoginRequest, db: Session = Depends(get_db)):
    """
    Create a new user with the given email/password and return a JWT.

    Request body:
        email: Unique user email.
        password: Plaintext password to be hashed using pbkdf2_sha256.

    Behavior:
        - Returns 400 if the email already exists.
        - On success, creates the user, hashes the password, and returns a Token.

    Returns:
        Token: {access_token, token_type}
    """
    existing = db.execute(select(User).where(User.email == payload.email)).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    user = User(
        email=payload.email,
        password_hash=pbkdf2_sha256.hash(payload.password),
        full_name=None,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = _create_access_token(subject=user.id)
    return Token(access_token=token, token_type="bearer")


# PUBLIC_INTERFACE
@router.post(
    "/login",
    response_model=Token,
    summary="Login",
    description="Authenticate a user by email and password and return a JWT access token.",
    tags=["auth"],
)
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
@router.get(
    "/me",
    response_model=UserSchema,
    summary="Get current user",
    description="Return the currently authenticated user derived from the Bearer JWT token.",
    tags=["auth"],
)
def me(current_user: User = Depends(lambda request, db=Depends(get_db): get_current_user(request, db))):
    """
    Return the currently authenticated user.

    The user is resolved from the Authorization: Bearer token by the `get_current_user`
    dependency. If the token is invalid, expired, or the user does not exist, a 401
    will be raised before this handler is executed.
    """
    return current_user


# PUBLIC_INTERFACE
def get_current_user(request: Request, db: Session) -> User:
    """
    Resolve the current authenticated user from a Bearer JWT token.

    This function is intended to be used with FastAPI's dependency system, e.g.:

        current_user: User = Depends(
            lambda request, db=Depends(get_db): get_current_user(request, db)
        )

    It performs the following steps:
        1. Reads the Authorization header.
        2. Extracts and decodes the Bearer token using JWT_SECRET / JWT_ALGORITHM.
        3. Validates the payload against `_TokenPayload`.
        4. Loads the User from the database.
        5. Raises HTTP 401 on any failure.

    Args:
        request: FastAPI Request object used to read headers.
        db: SQLAlchemy session.

    Returns:
        User: The authenticated User instance.

    Raises:
        HTTPException(401): If the header is missing, token is invalid/expired,
            or the user does not exist.
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
        )

    token = auth_header.split(" ", 1)[1].strip()
    try:
        decoded = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        data = _TokenPayload(**decoded)
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    user = db.get(User, data.sub)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    return user
