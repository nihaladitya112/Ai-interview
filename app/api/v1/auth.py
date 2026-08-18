from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta, timezone
from fastapi_limiter.depends import RateLimiter
import uuid

from app.core import security
from app.core.config import settings
from app.core.database import get_db
from app.models.user import User, UserRole
from app.models.refresh_token import RefreshToken

router = APIRouter(prefix="/auth", tags=["auth"])

from pydantic import BaseModel
from typing import Optional
from app.models.candidate import CandidateProfile

class UserRegister(BaseModel):
    email: str
    password: str
    first_name: str
    last_name: str
    phone: Optional[str] = None
    role: str = "CANDIDATE"

# ----------------------------------------------------------------------
# Register
# ----------------------------------------------------------------------
@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserRegister,
    db: AsyncSession = Depends(get_db),
) -> dict:
    # Check for duplicate email
    result = await db.execute(select(User).where(User.email == user_data.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )
    hashed = security.get_password_hash(user_data.password)
    new_user = User(email=user_data.email, hashed_password=hashed, role=UserRole(user_data.role))
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    
    # Create Candidate Profile with the details
    profile = CandidateProfile(
        user_id=new_user.id,
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        phone=user_data.phone
    )
    db.add(profile)
    await db.commit()
    
    return {"id": str(new_user.id), "email": new_user.email, "role": new_user.role.value}

# ----------------------------------------------------------------------
# Login
# ----------------------------------------------------------------------
@router.post("/login")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
) -> dict:
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalar_one_or_none()
    if not user or not security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    access_token = security.create_access_token({"sub": str(user.id), "role": user.role.value})
    refresh_token_raw = security.create_refresh_token({"sub": str(user.id)})
    # Store refresh token
    refresh_obj = RefreshToken(
        user_id=user.id,
        token=refresh_token_raw,
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    db.add(refresh_obj)
    await db.commit()
    return {"access_token": access_token, "refresh_token": refresh_token_raw}

# ----------------------------------------------------------------------
# Refresh
# ----------------------------------------------------------------------
@router.post("/refresh")
async def refresh(
    refresh_token: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    # Validate token format and expiration
    try:
        payload = security.decode_token(refresh_token)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    sub = payload.get("sub")
    if not sub:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token == refresh_token).where(RefreshToken.user_id == uuid.UUID(sub))
    )
    token_obj = result.scalar_one_or_none()
    if token_obj is None or token_obj.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token expired or revoked")
    access_token = security.create_access_token({"sub": sub, "role": token_obj.user.role.value})
    return {"access_token": access_token}
