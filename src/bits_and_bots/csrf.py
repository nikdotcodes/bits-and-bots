"""Signed double-submit CSRF protection for browser form submissions."""
import hashlib
import hmac
import secrets
from urllib.parse import parse_qs

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from .config import COOKIE_SECURE, SECRET_KEY

CSRF_COOKIE = "club_csrf"
SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}


def _signature(token: str) -> str:
    return hmac.new(SECRET_KEY.encode(), token.encode(), hashlib.sha256).hexdigest()


def _valid_cookie(value: str | None) -> str | None:
    if not value or "." not in value:
        return None
    token, signature = value.rsplit(".", 1)
    if hmac.compare_digest(_signature(token), signature):
        return token
    return None



async def _read_body_limited(request: Request, limit: int) -> bytes | None:
    declared = request.headers.get("content-length")
    if declared:
        try:
            if int(declared) > limit:
                return None
        except ValueError:
            return None

    chunks: list[bytes] = []
    total = 0
    async for chunk in request.stream():
        total += len(chunk)
        if total > limit:
            return None
        chunks.append(chunk)
    body = b"".join(chunks)
    request._body = body
    sent = False

    async def replay():
        nonlocal sent
        if not sent:
            sent = True
            return {"type": "http.request", "body": body, "more_body": False}
        return {"type": "http.disconnect"}

    request._receive = replay
    return body


def _secure_response(response: Response) -> Response:
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    response.headers.setdefault(
        "Content-Security-Policy",
        "default-src 'self'; base-uri 'self'; form-action 'self'; "
        "frame-ancestors 'none'; object-src 'none'; upgrade-insecure-requests; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com",
    )
    if COOKIE_SECURE:
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    return response


class CSRFSecurityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        cookie_value = request.cookies.get(CSRF_COOKIE)
        token = _valid_cookie(cookie_value)
        new_cookie = token is None
        if new_cookie:
            token = secrets.token_urlsafe(32)
        request.state.csrf_token = token

        if request.method.upper() not in SAFE_METHODS:
            content_type = request.headers.get("content-type", "").lower()
            supplied = request.headers.get("x-csrf-token")
            if "application/x-www-form-urlencoded" in content_type:
                body = await _read_body_limited(request, 64 * 1024)
                if body is None:
                    return _secure_response(Response("Request body too large", status_code=413))
                values = parse_qs(body.decode("utf-8", "replace"))
                supplied = (values.get("_csrf") or [None])[0]
            elif "multipart/form-data" in content_type:
                body = await _read_body_limited(request, 6 * 1024 * 1024)
                if body is None:
                    return _secure_response(Response("Request body too large", status_code=413))
                form = await request.form(max_files=1, max_fields=40)
                supplied = str(form.get("_csrf", ""))

            if not supplied or not hmac.compare_digest(str(supplied), token):
                response = Response(
                    "CSRF validation failed", status_code=403,
                    headers={"Cache-Control": "no-store"},
                )
                if new_cookie:
                    response.set_cookie(
                        CSRF_COOKIE, f"{token}.{_signature(token)}",
                        httponly=True, secure=COOKIE_SECURE, samesite="lax",
                        path="/", max_age=86400,
                    )
                return _secure_response(response)

        response = await call_next(request)
        if new_cookie:
            response.set_cookie(
                CSRF_COOKIE, f"{token}.{_signature(token)}",
                httponly=True, secure=COOKIE_SECURE, samesite="lax",
                path="/", max_age=86400,
            )
        return _secure_response(response)
