import secrets
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

import jwt as pyjwt
from fastapi import Depends, HTTPException, Request

from .config import SECRET_KEY
from .database import db

SESSION_COOKIE = "club_session"
SESSION_TTL = timedelta(hours=8)


def create_session(volunteer_id: int) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": str(volunteer_id),
        "iat": int(now.timestamp()),
        "exp": int((now + SESSION_TTL).timestamp()),
        "jti": secrets.token_hex(8),
    }
    return pyjwt.encode(payload, SECRET_KEY, algorithm="HS256")


def get_current_volunteer(request: Request) -> dict[str, Any] | None:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return None
    try:
        payload = pyjwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        with db() as supabase:
            response = supabase.table("volunteers").select("*").eq(
                "id", int(payload["sub"])
            ).execute()
            return response.data[0] if response.data else None
    except Exception:
        return None


async def require_volunteer(request: Request) -> dict[str, Any]:
    volunteer = get_current_volunteer(request)
    if not volunteer:
        raise HTTPException(status_code=303, headers={"Location": "/volunteers/login"})
    return volunteer


Volunteer = Annotated[dict[str, Any], Depends(require_volunteer)]
