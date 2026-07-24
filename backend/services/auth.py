# backend/services/auth.py
"""JWT authentication service — token creation, password hashing, user validation."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

logger = logging.getLogger(__name__)

# Graceful imports
try:
    from jose import JWTError, jwt
    _jwt_available = True
except ImportError:
    _jwt_available = False
    logger.warning("python-jose not installed. Auth disabled. Install: pip install python-jose[cryptography]")

try:
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    _passlib_available = True
except ImportError:
    pwd_context = None
    _passlib_available = False
    logger.warning("passlib not installed. Auth disabled. Install: pip install passlib[bcrypt]")

from backend.services.config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES


# ─── Password Hashing ───

def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    if not _passlib_available:
        raise RuntimeError("passlib not installed")
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    if not _passlib_available:
        return False
    return pwd_context.verify(plain_password, hashed_password)


# ─── JWT Tokens ───

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    if not _jwt_available:
        raise RuntimeError("python-jose not installed")

    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    """Decode and validate a JWT access token. Returns payload or None."""
    if not _jwt_available:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


def is_auth_available() -> bool:
    """Check if all auth dependencies are installed."""
    return _jwt_available and _passlib_available
