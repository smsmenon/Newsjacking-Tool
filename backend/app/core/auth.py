"""
Clerk JWT authentication for FastAPI.
Validates tokens via Clerk's JWKS endpoint.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from jose.backends import RSAKey

from app.core.config import settings

logger = logging.getLogger("tada.auth")

_bearer = HTTPBearer(auto_error=True)
_jwks_cache: Optional[dict] = None


async def _get_jwks() -> dict:
    """Fetch and cache Clerk's JWKS."""
    global _jwks_cache
    if _jwks_cache is not None:
        return _jwks_cache

    async with httpx.AsyncClient() as client:
        resp = await client.get(settings.CLERK_JWKS_URL, timeout=5.0)
        resp.raise_for_status()
        _jwks_cache = resp.json()
    return _jwks_cache


@dataclass
class CurrentUser:
    user_id: str
    name: str
    email: Optional[str] = None
    org_id: Optional[str] = None
    roles: list[str] = None

    def __post_init__(self):
        if self.roles is None:
            self.roles = []


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> CurrentUser:
    """
    FastAPI dependency — validates Clerk JWT and returns CurrentUser.

    Raises 401 if token is missing, expired, or invalid.
    """
    token = credentials.credentials

    try:
        jwks = await _get_jwks()
        payload = jwt.decode(
            token,
            jwks,
            algorithms=["RS256"],
            options={"verify_aud": False},  # Clerk tokens don't always set aud
        )
    except JWTError as exc:
        logger.warning("JWT validation failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing sub claim")

    # Clerk stores metadata under `metadata` or `public_metadata`
    meta = payload.get("public_metadata", {})
    name = payload.get("name") or meta.get("name") or user_id
    email = payload.get("email")
    org_id = payload.get("org_id")
    roles = payload.get("roles") or meta.get("roles") or []

    return CurrentUser(
        user_id=user_id,
        name=name,
        email=email,
        org_id=org_id,
        roles=roles if isinstance(roles, list) else [roles],
    )
