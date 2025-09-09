from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from fastapi.responses import RedirectResponse
from .config import get_settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)

settings = get_settings()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def authenticate_user(username: str, password: str) -> bool:
    if username == settings.auth_username and password == settings.auth_password:
        return True
    return False


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, settings.secret_key, algorithm=settings.algorithm
    )
    return encoded_jwt


async def get_current_user(
    request: Request, token: Optional[str] = Depends(oauth2_scheme)
):
    # Check for token in Authorization header
    if token:
        try:
            payload = jwt.decode(
                token, settings.secret_key, algorithms=[settings.algorithm]
            )
            username: str = payload.get("sub")
            if username is None:
                return None
            return username
        except JWTError:
            return None

    # Check for token in cookies
    token = request.cookies.get("access_token")
    if token:
        try:
            # Remove "Bearer " prefix if present
            if token.startswith("Bearer "):
                token = token[7:]
            payload = jwt.decode(
                token, settings.secret_key, algorithms=[settings.algorithm]
            )
            username: str = payload.get("sub")
            if username is None:
                return None
            return username
        except JWTError:
            return None

    return None


async def require_auth(
    request: Request, current_user: Optional[str] = Depends(get_current_user)
):
    if current_user is None:
        # For API requests, return 401
        if request.url.path.startswith("/api/"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated",
                headers={"WWW-Authenticate": "Bearer"},
            )
        # For web requests, redirect to login
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    return current_user
