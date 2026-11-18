from datetime import UTC, datetime

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse

from ..config import BASE_URL
from ..database import db
from ..templates import templates

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
    return templates.TemplateResponse(request, "privacy-notice.html", {"BASE_URL": BASE_URL})


# ---------------------------------------------------------------------------
# Forms: contact (parents) and consent (parent/guardian only)
# ---------------------------------------------------------------------------


@router.get("/contact", response_class=HTMLResponse)
async def contact_page(request: Request, sent: bool = False):
    return templates.TemplateResponse(request, "contact.html", {"sent": sent})


@router.post("/contact")
async def contact_submit(
    name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(""),
    child_year_group: str = Form(""),
    message: str = Form(...),
):
    try:
        with db() as supabase:
            supabase.table("contact_messages").insert(
                {
                    "name": name.strip(),
                    "email": email.strip(),
                    "phone": phone.strip(),
                    "child_year_group": child_year_group,
                    "message": message.strip(),
                    "created_at": datetime.now(UTC).isoformat(),
                }
            ).execute()
        return RedirectResponse("/contact?sent=true", status_code=303)
    except Exception as e:
        print(f"Error saving contact message: {e}")
        return RedirectResponse("/contact?error=true", status_code=303)


@router.get("/consent", response_class=HTMLResponse)
async def consent_page(request: Request, sent: bool = False):
    return templates.TemplateResponse(request, "consent.html", {"sent": sent})


@router.post("/consent")
async def consent_submit(
    child_first_name: str = Form(...),
    child_last_initial: str = Form(...),
    child_year_group: str = Form(...),
    parent_name: str = Form(...),
    parent_email: str = Form(...),
    parent_phone: str = Form(""),
    emergency_contact: str = Form(""),
    medical_notes: str = Form(""),
    ai_tools_consent: str = Form("no"),
    signature_name: str = Form(...),
    signed_date: str = Form(...),
    consent_file: UploadFile | None = File(None),
):
    file_name, file_data = "", None
    if consent_file and consent_file.filename:
        data = await consent_file.read()
        if len(data) > 5 * 1024 * 1024:
            raise HTTPException(413, "Scan must be under 5 MB (PDF please).")
        file_name, file_data = consent_file.filename, data
    
    try:
        with db() as supabase:
            supabase.table("consent_submissions").insert(
                {
                    "child_first_name": child_first_name.strip(),
                    "child_last_initial": child_last_initial.strip(),
                    "child_year_group": child_year_group,
                    "parent_name": parent_name.strip(),
                    "parent_email": parent_email.strip(),
                    "parent_phone": parent_phone.strip(),
                    "emergency_contact": emergency_contact.strip(),
                    "medical_notes": medical_notes.strip(),
                    "ai_tools_consent": ai_tools_consent,
                    "signature_name": signature_name.strip(),
                    "signed_date": signed_date,
                    "file_name": file_name,
                    "file_data": file_data,
                    "created_at": datetime.now(UTC).isoformat(),
                }
            ).execute()
        return RedirectResponse("/consent?sent=true", status_code=303)
    except Exception as e:
        print(f"Error saving consent submission: {e}")
        return RedirectResponse("/consent?error=true", status_code=303)
