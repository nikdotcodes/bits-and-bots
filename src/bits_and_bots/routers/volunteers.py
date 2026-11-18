"""Administrator-only access to sensitive consent and contact records."""
from urllib.parse import quote, urlparse

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from ..audit import record_event
from ..config import CONSENT_BUCKET
from ..database import db
from ..security import Admin
from ..templates import templates

router = APIRouter()


@router.get("/volunteers", response_class=HTMLResponse)
async def volunteer_dashboard(request: Request, volunteer: Admin):
    try:
        with db() as supabase:
            consents_response = supabase.table("consent_submissions").select("*").order(
                "created_at", desc=True
            ).limit(50).execute()
            messages_response = supabase.table("contact_messages").select("*").order(
                "created_at", desc=True
            ).limit(50).execute()
            resources_response = supabase.table("teaching_resources").select("*").order(
                "category"
            ).order("title").execute()
            consents = consents_response.data or []
            messages = messages_response.data or []
            resources = resources_response.data or []
            pending = sum(1 for c in consents if c.get("status") == "pending")
            record_event(
                actor_id=volunteer["id"], action="admin.dashboard.view",
                resource_type="admin_dashboard",
                request_id=getattr(request.state, "request_id", None),
            )
            return templates.TemplateResponse(
                request, "dashboard.html",
                {
                    "volunteer": volunteer, "consents": consents,
                    "messages": messages, "resources": resources, "pending": pending,
                },
            )
    except Exception:
        raise HTTPException(503, "Dashboard temporarily unavailable")


@router.post("/volunteers/consents/{consent_id}/signoff")
async def sign_off_consent(
    request: Request, consent_id: int, volunteer: Admin,
    decision: str = Form(...),
):
    if decision not in {"approve", "reject"}:
        raise HTTPException(422, "Invalid consent decision")
    try:
        with db() as supabase:
            result = supabase.rpc(
                "signoff_consent_with_audit",
                {
                    "p_consent_id": consent_id,
                    "p_actor_id": str(volunteer["id"]),
                    "p_actor_email": volunteer["email"],
                    "p_decision": decision,
                    "p_request_id": getattr(request.state, "request_id", None),
                },
            ).execute()
            if result.data is not True:
                existing = supabase.table("consent_submissions").select(
                    "id,status"
                ).eq("id", consent_id).limit(1).execute()
                if not existing.data:
                    raise HTTPException(404, "Consent not found")
                raise HTTPException(409, "Consent has already been processed")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(503, "Consent update could not be completed")
    return RedirectResponse("/volunteers", status_code=303)


@router.get("/volunteers/consents/{consent_id}/file")
async def download_consent_file(consent_id: int, volunteer: Admin):
    try:
        with db() as supabase:
            response = supabase.table("consent_submissions").select(
                "file_name,storage_path"
            ).eq("id", consent_id).limit(1).execute()
            if not response.data or not response.data[0].get("storage_path"):
                raise HTTPException(404, "No scanned copy stored for this consent.")
            row = response.data[0]
            content = supabase.storage.from_(CONSENT_BUCKET).download(row["storage_path"])
            record_event(
                actor_id=volunteer["id"], action="consent.document.download",
                resource_type="consent_submission", resource_id=consent_id,
            )
            filename = (row.get("file_name") or "consent-document").replace("\\r", "").replace("\\n", "")
            safe_ascii = "".join(c for c in filename if c.isascii() and c.isalnum() or c in "._- ")[:120]
            disposition = f"attachment; filename=\"{safe_ascii or 'consent-document'}\"; filename*=UTF-8''{quote(filename, safe='')}"
            suffix = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
            media_type = {"pdf": "application/pdf", "jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png"}.get(suffix, "application/octet-stream")
            return Response(
                content=content, media_type=media_type,
                headers={
                    "Content-Disposition": disposition,
                    "Cache-Control": "private, no-store",
                    "X-Content-Type-Options": "nosniff",
                },
            )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(503, "Document temporarily unavailable")


@router.post("/volunteers/resources")
async def add_resource(
    request: Request, volunteer: Admin,
    title: str = Form(...), url: str = Form(...),
    description: str = Form(""), category: str = Form("general"),
):
    parsed = urlparse(url.strip())
    if parsed.scheme not in {"https", "http"} or not parsed.netloc:
        raise HTTPException(422, "Resource URL must be an absolute HTTP(S) URL")
    try:
        with db() as supabase:
            result = supabase.table("teaching_resources").insert({
                "title": title.strip()[:160],
                "description": description.strip()[:1000],
                "url": url.strip(),
                "category": category.strip()[:60],
                "added_by": volunteer["email"],
            }).execute()
            record_event(
                actor_id=volunteer["id"], action="resource.created",
                resource_type="teaching_resource",
                resource_id=result.data[0].get("id") if result.data else None,
                request_id=getattr(request.state, "request_id", None),
            )
    except Exception:
        raise HTTPException(503, "Resource could not be saved")
    return RedirectResponse("/volunteers", status_code=303)
