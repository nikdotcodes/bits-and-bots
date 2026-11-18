"""Validated application configuration.

Production deployments fail closed when required secrets or URLs are missing.
"""

import base64
import json
import os
import secrets
from urllib.parse import urlparse

# Load .env only for local development. Production secrets must come from the host.
if os.getenv("ENVIRONMENT", "development").lower() != "production":
    from dotenv import load_dotenv

    load_dotenv()

ENVIRONMENT = os.getenv("ENVIRONMENT", "development").lower()
IS_PRODUCTION = ENVIRONMENT == "production"

SECRET_KEY = os.getenv("SECRET_KEY", "") or (
    "" if IS_PRODUCTION else secrets.token_urlsafe(48)
)
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8000").rstrip("/")
COOKIE_SECURE = IS_PRODUCTION or urlparse(BASE_URL).scheme == "https"
SESSION_TTL_SECONDS = int(os.getenv("SESSION_TTL_SECONDS", "28800"))
CONSENT_BUCKET = os.getenv("CONSENT_BUCKET", "consent-documents")
MAX_UPLOAD_BYTES = 5 * 1024 * 1024


def validate_config() -> None:
    required = {
        "SECRET_KEY": SECRET_KEY,
        "SUPABASE_URL": SUPABASE_URL,
        "SUPABASE_KEY": SUPABASE_KEY,
        "BASE_URL": BASE_URL,
    }
    missing = [key for key, value in required.items() if not value.strip()]
    if missing:
        raise RuntimeError("Missing required configuration: " + ", ".join(missing))
    if len(SECRET_KEY) < 32:
        raise RuntimeError("SECRET_KEY must contain at least 32 characters")
    parsed = urlparse(BASE_URL)
    if not parsed.netloc or parsed.scheme not in ("http", "https"):
        raise RuntimeError("BASE_URL must be an absolute HTTP or HTTPS URL")
    if IS_PRODUCTION and parsed.scheme != "https":
        raise RuntimeError("Production BASE_URL must be an absolute HTTPS URL")
    supabase_parsed = urlparse(SUPABASE_URL)
    if supabase_parsed.scheme != "https" or not supabase_parsed.netloc:
        raise RuntimeError("SUPABASE_URL must be an absolute HTTPS URL")
    if SUPABASE_KEY.startswith("sb_publishable_"):
        raise RuntimeError("SUPABASE_KEY must be a server-side secret/service-role key")
    if not SUPABASE_KEY.startswith("sb_secret_"):
        # Legacy Supabase service_role keys are JWTs. Reject anon/publishable keys.
        try:
            payload = SUPABASE_KEY.split(".")[1]
            payload += "=" * (-len(payload) % 4)
            role = json.loads(base64.urlsafe_b64decode(payload)).get("role")
        except Exception:
            role = None
        if role != "service_role":
            raise RuntimeError(
                "SUPABASE_KEY must be a server-side secret/service-role key"
            )
    if SESSION_TTL_SECONDS < 300 or SESSION_TTL_SECONDS > 86400:
        raise RuntimeError("SESSION_TTL_SECONDS must be between 300 and 86400")
