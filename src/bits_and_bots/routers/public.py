import logging
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse

from ..config import BASE_URL, CONSENT_BUCKET, MAX_UPLOAD_BYTES
from ..database import db
from ..security import consume_rate_limit
from ..templates import templates

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(request, "home.html", {})


@router.get("/about", response_class=HTMLResponse)
async def about(request: Request):
    return templates.TemplateResponse(request, "about.html", {})


@router.get("/blog", response_class=HTMLResponse)
async def blog(request: Request):
    posts = [
        {
            "slug": "week-1-hello-microbit",
            "title": "Week 1: Hello, micro:bit!",
            "date": "2026-09-16",
            "body": "Our first session: unplugged 'robot teacher' games, then flashing hearts and scrolling names in MakeCode. Every child left with a working name badge.",
        },
        {
            "slug": "week-4-rock-paper-scissors",
            "title": "Week 4: Rock, paper, scissors",
            "date": "2026-10-07",
            "body": "Accelerometers, random numbers and a very competitive tournament. We also talked about how the micro:bit 'senses' the world, just like a games controller.",
        },
        {
            "slug": "moving-to-python",
            "title": "Getting ready for Python",
            "date": "2026-11-04",
            "body": "Next term our older coders swap blocks for text using the micro:bit Python Editor. Same board, new superpowers - and yes, there will be emoji on the LED display.",
        },
    ]
    return templates.TemplateResponse(request, "blog.html", {"posts": posts})


@router.get("/microbit", response_class=HTMLResponse)
async def microbit_page(request: Request):
    return templates.TemplateResponse(request, "microbit.html", {})


@router.get("/python", response_class=HTMLResponse)
async def python_page(request: Request):
    return templates.TemplateResponse(request, "python.html", {})


@router.get("/resources", response_class=HTMLResponse)
async def student_resources(request: Request):
    """No login needed - safe, curated links for children."""
    student_links = [
        {
            "title": "MakeCode for micro:bit",
            "url": "https://makecode.microbit.org/",
            "blurb": "Drag blocks, flash your micro:bit, play your game.",
        },
        {
            "title": "micro:bit Projects",
            "url": "https://microbit.org/projects/make-it-code-it/",
            "blurb": "Step-by-step projects: step counters, magic wands, quiet monsters.",
        },
        {
            "title": "Python Editor for micro:bit",
            "url": "https://python.microbit.org/v/3",
            "blurb": "Ready for text code? Try MicroPython in the browser.",
        },
        {
            "title": "Code.org Express",
            "url": "https://studio.code.org/s/express",
            "blurb": "Fun puzzles to practise the thinking we use in club.",
        },
        {
            "title": "Scratch",
            "url": "https://scratch.mit.edu/",
            "blurb": "Make games and animations with blocks at home.",
        },
    ]
    return templates.TemplateResponse(
        request, "resources.html", {"links": student_links}
    )


@router.get("/safety/online", response_class=HTMLResponse)
async def online_safety(request: Request):
    return templates.TemplateResponse(request, "online-safety.html", {})


@router.get("/safety/ai", response_class=HTMLResponse)
async def ai_safety(request: Request):
    return templates.TemplateResponse(request, "ai-safety.html", {})


@router.get("/donate", response_class=HTMLResponse)
async def donate(request: Request):
    return templates.TemplateResponse(request, "donate.html", {})


@router.get("/privacy-notice", response_class=HTMLResponse)
async def privacy_notice(request: Request):
    return templates.TemplateResponse(
        request, "privacy-notice.html", {"BASE_URL": BASE_URL}
    )


# ---------------------------------------------------------------------------
# Forms: contact (parents) and consent (parent/guardian only)
# ---------------------------------------------------------------------------


@router.get("/contact", response_class=HTMLResponse)
async def contact_page(request: Request, sent: bool = False):
    return templates.TemplateResponse(request, "contact.html", {"sent": sent})


@router.post("/contact")
async def contact_submit(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(""),
    child_year_group: str = Form(""),
    message: str = Form(...),
):
    client_ip = request.client.host if request.client else "unknown"
    if not name.strip() or not message.strip() or "@" not in email:
        raise HTTPException(422, "Please provide a name, valid email and message.")
    if not consume_rate_limit(f"contact:{client_ip}", limit=10, window_seconds=600):
        raise HTTPException(429, "Too many submissions. Please try again later.")
    try:
        with db() as supabase:
            supabase.table("contact_messages").insert(
                {
                    "name": name.strip()[:160],
                    "email": email.strip().lower()[:254],
                    "phone": phone.strip()[:40],
                    "child_year_group": child_year_group[:40],
                    "message": message.strip()[:10000],
                    "created_at": datetime.now(UTC).isoformat(),
                }
            ).execute()
        return RedirectResponse("/contact?sent=true", status_code=303)
    except Exception: # noqa: BLE001
        return RedirectResponse("/contact?error=true", status_code=303)


@router.get("/consent", response_class=HTMLResponse)
async def consent_page(request: Request, sent: bool = False):
    return templates.TemplateResponse(request, "consent.html", {"sent": sent})


@router.post("/consent")
async def consent_submit(
    request: Request,
    child_first_name: str = Form(...),
    child_last_initial: str = Form(...),
    child_year_group: str = Form(...),
    parent_name: str = Form(...),
    parent_email: str = Form(...),
    parent_phone: str = Form(""),
    emergency_contact: str = Form(""),
    medical_notes: str = Form(""),
    medical_consent: str = Form("no"),
    ai_tools_consent: str = Form("no"),
    signature_name: str = Form(...),
    signed_date: str = Form(...),
    consent_file: UploadFile | None = File(None),
):
    client_ip = request.client.host if request.client else "unknown"
    if not consume_rate_limit(f"consent:{client_ip}", limit=5, window_seconds=3600):
        raise HTTPException(429, "Too many submissions. Please try again later.")
    if (
        not all(
            [
                child_first_name.strip(),
                child_last_initial.strip(),
                child_year_group.strip(),
                parent_name.strip(),
                parent_email.strip(),
                signature_name.strip(),
                signed_date.strip(),
            ]
        )
        or "@" not in parent_email
    ):
        raise HTTPException(422, "Please complete all required consent details.")
    if medical_notes.strip() and medical_consent != "yes":
        raise HTTPException(422, "Explicit medical information consent is required.")
    if medical_consent not in {"yes", "no"} or ai_tools_consent not in {"yes", "no"}:
        raise HTTPException(422, "Invalid consent selection.")

    file_name, storage_path = "", None
    if consent_file and consent_file.filename:
        data = await consent_file.read(MAX_UPLOAD_BYTES + 1)
        if len(data) > MAX_UPLOAD_BYTES:
            raise HTTPException(413, "Scan must be under 5 MB.")
        content_type = (consent_file.content_type or "").lower()
        signatures = {
            "application/pdf": data.startswith(b"%PDF-"),
            "image/jpeg": data.startswith(b"\\xff\\xd8\\xff"),
            "image/png": data.startswith(b"\\x89PNG\\r\\n\\x1a\\n"),
        }
        if content_type not in signatures or not signatures[content_type]:
            raise HTTPException(415, "Only valid PDF, JPEG or PNG files are accepted.")
        suffix = {"application/pdf": ".pdf", "image/jpeg": ".jpg", "image/png": ".png"}[
            content_type
        ]
        file_name = (
            Path(consent_file.filename).name.replace("\\x00", "")[:180]
            or f"consent{suffix}"
        )
        storage_path = f"submissions/{uuid4().hex}{suffix}"

    try:
        with db() as supabase:
            if storage_path:
                supabase.storage.from_(CONSENT_BUCKET).upload(
                    storage_path,
                    data,
                    file_options={"content-type": content_type, "upsert": "false"},
                )
            payload = {
                "child_first_name": child_first_name.strip()[:100],
                "child_last_initial": child_last_initial.strip()[:1].upper(),
                "child_year_group": child_year_group.strip()[:40],
                "parent_name": parent_name.strip()[:160],
                "parent_email": parent_email.strip().lower()[:254],
                "parent_phone": parent_phone.strip()[:40],
                "emergency_contact": emergency_contact.strip()[:300],
                "medical_notes": medical_notes.strip()[:5000],
                "medical_consent": medical_consent,
                "ai_tools_consent": (
                    ai_tools_consent if ai_tools_consent in {"yes", "no"} else "no"
                ),
                "signature_name": signature_name.strip()[:160],
                "signed_date": signed_date,
                "file_name": file_name,
                "storage_path": storage_path,
                "created_at": datetime.now(UTC).isoformat(),
            }
            supabase.rpc(
                "submit_consent_with_audit",
                {
                    "p_payload": payload,
                    "p_request_id": getattr(request.state, "request_id", None),
                },
            ).execute()
        return RedirectResponse("/consent?sent=true", status_code=303)
    except Exception:
        logger.exception("Consent submission failed")
        # A network timeout may occur after the RPC committed. Keep the object if
        # a consent row references it; otherwise remove the orphaned upload.
        if storage_path:
            try:
                with db() as supabase:
                    linked = (
                        supabase.table("consent_submissions")
                        .select("id")
                        .eq("storage_path", storage_path)
                        .limit(1)
                        .execute()
                    )
                    if not linked.data:
                        supabase.storage.from_(CONSENT_BUCKET).remove([storage_path])
            except Exception: # noqa: BLE001
                logger.warning(
                    "Could not verify or clean up an uploaded consent document",
                    exc_info=False,
                )
        return RedirectResponse("/consent?error=true", status_code=303)
