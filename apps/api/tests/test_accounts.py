import uuid
from unittest.mock import patch

import pytest
from app.api.deps import get_current_user
from app.api.routes.auth import (
    Credentials,
    PasswordChange,
    change_password,
    login,
    quota_date,
    register,
)
from app.api.routes.campaigns import start_campaign
from app.core.config import Settings
from app.db.base import Base
from app.models.campaign import Campaign, CampaignStatus, DailyCampaignUsage, Workspace
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine


@pytest.mark.asyncio
async def test_password_change_revokes_sessions_and_quota_blocks_eleventh(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'accounts.db'}")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    settings = Settings(_env_file=None, app_auth_secret="test-secret-only")
    with patch("app.core.auth.get_settings", return_value=settings):
        async with factory() as session:
            credentials = Credentials(email="account@example.com", password="Old-password-123")
            result = await register(credentials, session)
            assert result.daily_runs_remaining == 10
            user = await get_current_user(session, "Bearer " + result.access_token)
            await change_password(PasswordChange(current_password=credentials.password,
                                                  new_password="New-password-123"), session, user)
            with pytest.raises(HTTPException) as revoked:
                await get_current_user(session, "Bearer " + result.access_token)
            assert revoked.value.status_code == 401
            with pytest.raises(HTTPException):
                await login(credentials, session)
            fresh = await login(Credentials(email=credentials.email, password="New-password-123"), session)
            assert (await get_current_user(session, "Bearer " + fresh.access_token)).id == user.id
            workspace = Workspace(id=uuid.uuid4(), name="Test", owner_user_id=user.id)
            session.add(workspace)
            campaign = Campaign(workspace_id=workspace.id, name="Quota test", target={}, limits={},
                                status=CampaignStatus.DRAFT)
            session.add(campaign)
            session.add(DailyCampaignUsage(user_id=user.id, usage_date=quota_date(), campaign_runs=10))
            await session.commit()
            with pytest.raises(HTTPException) as limited:
                await start_campaign(campaign.id, session, user)
            assert limited.value.status_code == 429
            assert campaign.status == CampaignStatus.DRAFT
    await engine.dispose()
