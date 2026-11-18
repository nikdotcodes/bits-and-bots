"""Volunteer authentication endpoints."""

import time
from collections import defaultdict, deque
from threading import Lock

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from ..audit import record_event
from ..config import COOKIE_SECURE, IS_PRODUCTION
from ..database import db
from ..passwords import hash_password, verify_password
from ..security import (
    SESSION_COOKIE,
    clear_session_cookie,
    consume_rate_limit,
    create_session,
    revoke_session,
    set_session_cookie,
)
from ..templates import templates

router = APIRouter()
_attempts: dict[str, deque[float]] = defaultdict(deque)
_attempt_lock = Lock()
_MAX_ATTEMPTS = 8
_WINDOW_SECONDS = 900


def _rate_limited(key: str) -> bool:
    now = time.monotonic()
    with _attempt_lock:
        attempts = _attempts[key]
        while attempts and now - attempts[0] > _WINDOW_SECONDS:
            attempts.popleft()
        if len(attempts) >= _MAX_ATTEMPTS:
            return True
        attempts.append(now)
        return False


@router.get("/volunteers/login", response_class=HTMLResponse)
async def login_page(request: Request, error: str = ""):
    return templates.TemplateResponse(request, "login.html", {"error": error})


@router.post("/volunteers/login")
async def login(request: Request, email: str = Form(...), password: str = Form(...)):
    normalized_email = email.lower().strip()
    client_ip = request.client.host if request.client else "unknown"
    rate_key = f"{client_ip}:{normalized_email}"
    if IS_PRODUCTION:
        if not consume_rate_limit(
            f"login:{rate_key}",
            limit=_MAX_ATTEMPTS,
            window_seconds=_WINDOW_SECONDS,
        ):
            return RedirectResponse("/volunteers/login?error=bad", status_code=303)
    elif _rate_limited(rate_key):
        return RedirectResponse("/volunteers/login?error=bad", status_code=303)

    try:
        with db() as supabase:
            response = (
                supabase.table("volunteers")
                .select("id,email,name,is_admin,password_hash")
                .eq("email", normalized_email)
                .limit(1)
                .execute()
            )
            if not response.data:
                return RedirectResponse("/volunteers/login?error=bad", status_code=303)
            row = response.data[0]
            valid, needs_rehash = verify_password(
                password, row.get("password_hash") or ""
            )
            if not valid:
                return RedirectResponse("/volunteers/login?error=bad", status_code=303)
            if needs_rehash:
                supabase.table("volunteers").update(
                    {"password_hash": hash_password(password)}
                ).eq("id", row["id"]).execute()

        token = create_session(row["id"])
        try:
            record_event(
                actor_id=row["id"],
                action="volunteer.login",
                resource_type="volunteer",
                resource_id=row["id"],
                request_id=getattr(request.state, "request_id", None),
            )
        except Exception:
            revoke_session(token)
            raise
        response = RedirectResponse("/volunteers", status_code=303)
        set_session_cookie(response, token, COOKIE_SECURE)
        return response
    except Exception:
        return RedirectResponse("/volunteers/login?error=bad", status_code=303)


@router.post("/volunteers/logout")
async def logout(request: Request):
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        try:
            from ..security import get_current_volunteer

            current = get_current_volunteer(request)
            revoke_session(token)
            if current:
                record_event(
                    actor_id=current["id"],
                    action="volunteer.logout",
                    resource_type="volunteer",
                    resource_id=current["id"],
                )
        except Exception:
            # Do not report a successful logout if server-side revocation failed.
            from fastapi import HTTPException

            raise HTTPException(
                503, "Session could not be securely revoked; please retry."
            )
    response = RedirectResponse("/", status_code=303)
    clear_session_cookie(response, COOKIE_SECURE)
    return response
