"""Opaque, revocable server-side volunteer sessions and role dependencies."""
import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

from fastapi import Depends, HTTPException, Request

from .config import IS_PRODUCTION, SECRET_KEY, SESSION_TTL_SECONDS
from .database import db

SESSION_COOKIE = "club_session"



def consume_rate_limit(key: str, *, limit: int, window_seconds: int) -> bool:
    """Shared atomic production rate limit; fail closed if the RPC is unavailable."""
    if not IS_PRODUCTION:
        return True
    key_hash = hmac.new(
        SECRET_KEY.encode(), key.encode(), hashlib.sha256
    ).hexdigest()
    try:
        with db() as client:
            result = client.rpc(
                "consume_rate_limit",
                {
                    "p_key_hash": key_hash,
                    "p_limit": limit,
                    "p_window_seconds": window_seconds,
                },
            ).execute()
        return result.data is True
    except Exception:
        return False


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_session(volunteer_id: int | str) -> str:
    token = secrets.token_urlsafe(48)
    now = datetime.now(UTC)
    with db() as client:
        client.table("volunteer_sessions").insert({
            "token_hash": _token_hash(token),
            "volunteer_id": str(volunteer_id),
            "expires_at": (now + timedelta(seconds=SESSION_TTL_SECONDS)).isoformat(),
            "created_at": now.isoformat(),
        }).execute()
    return token


def revoke_session(token: str | None) -> None:
    if not token:
        return
    with db() as client:
        client.table("volunteer_sessions").update({
            "revoked_at": datetime.now(UTC).isoformat()
        }).eq("token_hash", _token_hash(token)).is_("revoked_at", "null").execute()


def get_current_volunteer(request: Request) -> dict[str, Any] | None:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return None
    try:
        now = datetime.now(UTC).isoformat()
        with db() as client:
            sessions = client.table("volunteer_sessions").select(
                "volunteer_id"
            ).eq("token_hash", _token_hash(token)).is_(
                "revoked_at", "null"
            ).gt("expires_at", now).limit(1).execute()
            if not sessions.data:
                return None
            volunteers = client.table("volunteers").select(
                "id,email,name,is_admin"
            ).eq("id", sessions.data[0]["volunteer_id"]).limit(1).execute()
            return volunteers.data[0] if volunteers.data else None
    except Exception:
        return None


async def require_volunteer(request: Request) -> dict[str, Any]:
    volunteer = get_current_volunteer(request)
    if not volunteer:
        raise HTTPException(
            status_code=303, headers={"Location": "/volunteers/login"}
        )
    return volunteer


async def require_admin(volunteer: Annotated[dict[str, Any], Depends(require_volunteer)]):
    if not volunteer.get("is_admin"):
        raise HTTPException(status_code=403, detail="Administrator access required")
    return volunteer


Volunteer = Annotated[dict[str, Any], Depends(require_volunteer)]
Admin = Annotated[dict[str, Any], Depends(require_admin)]


def set_session_cookie(response, token: str, secure: bool) -> None:
    response.set_cookie(
        SESSION_COOKIE, token, max_age=SESSION_TTL_SECONDS,
        httponly=True, secure=secure, samesite="lax", path="/",
    )


def clear_session_cookie(response, secure: bool) -> None:
    response.delete_cookie(
        SESSION_COOKIE, path="/", secure=secure, httponly=True, samesite="lax"
    )
