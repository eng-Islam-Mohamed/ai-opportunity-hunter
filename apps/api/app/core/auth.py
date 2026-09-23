from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
import uuid

from fastapi import HTTPException, status

from app.core.config import get_settings

TOKEN_TTL_SECONDS = 60 * 60 * 24 * 7


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
    return "scrypt$" + base64.urlsafe_b64encode(salt + digest).decode()


def verify_password(password: str, stored: str) -> bool:
    try:
        _, encoded = stored.split("$", 1)
        raw = base64.urlsafe_b64decode(encoded.encode())
        return hmac.compare_digest(
            hashlib.scrypt(password.encode(), salt=raw[:16], n=2**14, r=8, p=1), raw[16:]
        )
    except (ValueError, TypeError):
        return False


def issue_token(user_id: uuid.UUID, password_hash: str) -> str:
    secret = get_settings().app_auth_secret
    if secret is None:
        raise RuntimeError("APP_AUTH_SECRET is not configured")
    payload = {"sub": str(user_id), "exp": int(time.time()) + TOKEN_TTL_SECONDS,
               "credential": hashlib.sha256(password_hash.encode()).hexdigest()}
    encoded = base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode()).decode()
    signature = hmac.new(secret.get_secret_value().encode(), encoded.encode(), hashlib.sha256).hexdigest()
    return encoded + "." + signature


def parse_token(token: str) -> tuple[uuid.UUID, str]:
    secret = get_settings().app_auth_secret
    if secret is None or "." not in token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    encoded, signature = token.rsplit(".", 1)
    expected = hmac.new(secret.get_secret_value().encode(), encoded.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    try:
        payload = json.loads(base64.urlsafe_b64decode(encoded.encode()))
        if int(payload["exp"]) < time.time():
            raise ValueError
        return uuid.UUID(payload["sub"]), payload["credential"]
    except (KeyError, ValueError, TypeError, json.JSONDecodeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required"
        ) from exc
