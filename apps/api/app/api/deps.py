import hashlib
import hmac
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import parse_token
from app.db.session import get_session
from app.models.campaign import User

DatabaseSession = Annotated[AsyncSession, Depends(get_session)]


async def get_current_user(
    session: DatabaseSession, authorization: Annotated[str | None, Header()] = None
) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    user_id, credential = parse_token(authorization.removeprefix("Bearer "))
    user = await session.get(User, user_id)
    if user is None or not hmac.compare_digest(
        credential, hashlib.sha256(user.password_hash.encode()).hexdigest()
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
