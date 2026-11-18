
from datetime import UTC, datetime

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from ..config import BASE_URL
from ..database import db
from ..passwords import pwd_context
from ..security import SESSION_COOKIE, create_session
from ..templates import templates

router = APIRouter()


# ---------------------------------------------------------------------------
# Email + password login
# ---------------------------------------------------------------------------


@router.get("/volunteers/login", response_class=HTMLResponse)
async def login_page(request: Request, error: str = ""):
    return templates.TemplateResponse(request, "login.html", {"error": error})


@router.post("/volunteers/login")
async def login(email: str = Form(...), password: str = Form(...)):
    try:
        with db() as supabase:
            response = supabase.table("volunteers").select("*").eq(
                "email", email.lower().strip()
            ).execute()

            if not response.data:
                return RedirectResponse("/volunteers/login?error=bad", status_code=303)

            row = response.data[0]
            if not row.get("password_hash") or not pwd_context.verify(
                password, row["password_hash"]
            ):
                return RedirectResponse("/volunteers/login?error=bad", status_code=303)

            resp = RedirectResponse("/volunteers", status_code=303)
            resp.set_cookie(
                SESSION_COOKIE,
                create_session(row["id"]),
                httponly=True,
                samesite="lax",
                secure=BASE_URL.startswith("https"),
            )
            return resp
    except Exception:
        return RedirectResponse("/volunteers/login?error=bad", status_code=303)


@router.get("/volunteers/logout")
async def logout():
    resp = RedirectResponse("/", status_code=303)
    resp.delete_cookie(SESSION_COOKIE)
    return resp
