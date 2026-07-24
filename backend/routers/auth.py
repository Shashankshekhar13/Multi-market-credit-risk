# backend/routers/auth.py
"""Authentication API endpoints — register, login, profile, token refresh."""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
import logging

from backend.services.database import get_db
from backend.services.auth import (
    hash_password, verify_password, create_access_token,
    decode_access_token, is_auth_available,
)
from backend.models import User, UserWatchlist

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/auth", tags=["auth"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


# ─── Schemas ───

class RegisterRequest(BaseModel):
    email: str = Field(..., min_length=5, max_length=255)
    password: str = Field(..., min_length=6, max_length=128)
    full_name: Optional[str] = None


class RegisterResponse(BaseModel):
    message: str
    user_id: int
    email: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    email: str
    full_name: Optional[str] = None


class UserProfile(BaseModel):
    id: int
    email: str
    full_name: Optional[str] = None
    is_active: bool
    created_at: str
    watchlist: list[str] = []


# ─── Auth Dependency ───

async def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """Extract current user from JWT token. Returns None if unauthenticated."""
    if not token or not is_auth_available():
        return None

    payload = decode_access_token(token)
    if payload is None:
        return None

    email = payload.get("sub")
    if email is None:
        return None

    try:
        stmt = select(User).where(User.email == email)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        return user
    except Exception:
        return None


async def require_auth(
    user: Optional[User] = Depends(get_current_user),
) -> User:
    """Require authentication — raises 401 if not logged in."""
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


# ─── Endpoints ───

@router.post("/register", response_model=RegisterResponse)
async def register(request: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """Register a new user account."""
    if not is_auth_available():
        raise HTTPException(status_code=503, detail="Auth dependencies not installed.")

    try:
        # Check if email already exists
        stmt = select(User).where(User.email == request.email.lower())
        existing = (await db.execute(stmt)).scalar_one_or_none()
        if existing:
            raise HTTPException(status_code=400, detail="Email already registered.")

        # Create user
        user = User(
            email=request.email.lower(),
            hashed_password=hash_password(request.password),
            full_name=request.full_name,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

        logger.info(f"New user registered: {user.email}")
        return RegisterResponse(message="User registered successfully.", user_id=user.id, email=user.email)

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Registration failed: {e}")
        raise HTTPException(status_code=500, detail="Registration failed. Database may be unavailable.")


@router.post("/login", response_model=TokenResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """Login and receive a JWT access token."""
    if not is_auth_available():
        raise HTTPException(status_code=503, detail="Auth dependencies not installed.")

    try:
        stmt = select(User).where(User.email == form_data.username.lower())
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user or not verify_password(form_data.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not user.is_active:
            raise HTTPException(status_code=400, detail="Account is disabled.")

        access_token = create_access_token(data={"sub": user.email})

        logger.info(f"User logged in: {user.email}")
        return TokenResponse(
            access_token=access_token,
            email=user.email,
            full_name=user.full_name,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login failed: {e}")
        raise HTTPException(status_code=500, detail="Login failed. Database may be unavailable.")


@router.get("/me", response_model=UserProfile)
async def get_profile(
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Get the current user's profile."""
    # Fetch watchlist
    watchlist_tickers = []
    try:
        stmt = select(UserWatchlist.ticker).where(UserWatchlist.user_id == user.id)
        result = await db.execute(stmt)
        watchlist_tickers = [row[0] for row in result.fetchall()]
    except Exception:
        pass

    return UserProfile(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        created_at=user.created_at.isoformat() if user.created_at else "",
        watchlist=watchlist_tickers,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(user: User = Depends(require_auth)):
    """Refresh the access token."""
    new_token = create_access_token(data={"sub": user.email})
    return TokenResponse(
        access_token=new_token,
        email=user.email,
        full_name=user.full_name,
    )


# ─── Watchlist Endpoints ───

class WatchlistRequest(BaseModel):
    ticker: str


@router.post("/watchlist")
async def add_to_watchlist(
    request: WatchlistRequest,
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Add a ticker to the user's watchlist."""
    try:
        # Check if already in watchlist
        stmt = select(UserWatchlist).where(
            UserWatchlist.user_id == user.id,
            UserWatchlist.ticker == request.ticker.upper(),
        )
        existing = (await db.execute(stmt)).scalar_one_or_none()
        if existing:
            return {"message": f"{request.ticker.upper()} is already in your watchlist."}

        entry = UserWatchlist(user_id=user.id, ticker=request.ticker.upper())
        db.add(entry)
        await db.commit()
        return {"message": f"{request.ticker.upper()} added to watchlist."}
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed: {e}")


@router.delete("/watchlist/{ticker}")
async def remove_from_watchlist(
    ticker: str,
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Remove a ticker from the user's watchlist."""
    try:
        stmt = select(UserWatchlist).where(
            UserWatchlist.user_id == user.id,
            UserWatchlist.ticker == ticker.upper(),
        )
        entry = (await db.execute(stmt)).scalar_one_or_none()
        if entry:
            await db.delete(entry)
            await db.commit()
            return {"message": f"{ticker.upper()} removed from watchlist."}
        return {"message": f"{ticker.upper()} not found in watchlist."}
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed: {e}")
