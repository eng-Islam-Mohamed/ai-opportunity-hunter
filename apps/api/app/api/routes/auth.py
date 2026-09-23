from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select

from app.api.deps import CurrentUser, DatabaseSession
from app.core.auth import hash_password, issue_token, verify_password
from app.models.campaign import DailyCampaignUsage, User

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])
DAILY_RUN_LIMIT = 10


def quota_date():
    return datetime.now(UTC).date()


class Credentials(BaseModel):
    email: str = Field(min_length=5, max_length=320)
    password: str = Field(min_length=10, max_length=128)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if "@" not in normalized or normalized.startswith("@") or normalized.endswith("@"):
            raise ValueError("Enter a valid email address.")
        return normalized


class AuthResponse(BaseModel):
    access_token: str
    email: str
    daily_runs_remaining: int


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: Credentials, session: DatabaseSession) -> AuthResponse:
    email = payload.email
    if await session.scalar(select(User).where(User.email == email)):
        raise HTTPException(status_code=409, detail="An account already exists for this email.")
    user = User(email=email, password_hash=hash_password(payload.password))
    session.add(user)
    await session.commit()
    return AuthResponse(access_token=issue_token(user.id, user.password_hash), email=user.email,
                        daily_runs_remaining=DAILY_RUN_LIMIT)


@router.post("/login", response_model=AuthResponse)
async def login(payload: Credentials, session: DatabaseSession) -> AuthResponse:
    user = await session.scalar(select(User).where(User.email == payload.email))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    usage = await session.scalar(
        select(DailyCampaignUsage).where(
            DailyCampaignUsage.user_id == user.id, DailyCampaignUsage.usage_date == quota_date()
        )
    )
    return AuthResponse(
        access_token=issue_token(user.id, user.password_hash),
        email=user.email,
        daily_runs_remaining=max(0, DAILY_RUN_LIMIT - (usage.campaign_runs if usage else 0)),
    )


@router.get("/me")
async def me(session: DatabaseSession, user: CurrentUser) -> dict:
    usage = await session.scalar(select(DailyCampaignUsage).where(
        DailyCampaignUsage.user_id == user.id, DailyCampaignUsage.usage_date == quota_date()
    ))
    return {"email": user.email, "daily_limit": DAILY_RUN_LIMIT,
            "daily_runs_remaining": max(0, DAILY_RUN_LIMIT - (usage.campaign_runs if usage else 0)),
            "reset_timezone": "UTC"}


class PasswordChange(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=10, max_length=128)


@router.post("/change-password")
async def change_password(
    payload: PasswordChange, session: DatabaseSession, user: CurrentUser
) -> dict:
    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect.")
    user.password_hash = hash_password(payload.new_password)
    await session.commit()
    return {"ok": True}
