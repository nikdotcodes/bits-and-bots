from datetime import UTC, datetime

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from ..database import db
from ..security import Volunteer
from ..templates import templates

router = APIRouter()


@router.get("/volunteers", response_class=HTMLResponse)
async def volunteer_dashboard(request: Request, volunteer: Volunteer = None):
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

            consents = consents_response.data
            messages = messages_response.data
            resources = resources_response.data
            pending = sum(1 for c in consents if c.get("status") == "pending")

            return templates.TemplateResponse(
                request,
                "dashboard.html",
                {
                    "volunteer": volunteer,
                    "consents": consents,
                    "messages": messages,
                    "resources": resources,
                    "pending": pending,
                },
            )
    except Exception as e:
        print(f"Error loading dashboard: {e}")
        raise HTTPException(500, "Error loading dashboard")


@router.post("/volunteers/consents/{consent_id}/signoff")
async def sign_off_consent(
    consent_id: int, volunteer: Volunteer = None, decision: str = Form(...)
):
    try:
        with db() as supabase:
            supabase.table("consent_submissions").update(
                {
                    "status": "signed_off" if decision == "approve" else "rejected",
                    "signed_off_by": volunteer["email"],
                    "signed_off_at": datetime.now(UTC).isoformat(),
                }
            ).eq("id", consent_id).execute()
    except Exception as e:
        print(f"Error signing off consent: {e}")
        raise HTTPException(500, "Error updating consent")
    return RedirectResponse("/volunteers", status_code=303)


@router.get("/volunteers/consents/{consent_id}/file")
async def download_consent_file(consent_id: int, volunteer: Volunteer = None):
    try:
        with db() as supabase:
            response = supabase.table("consent_submissions").select(
                "file_name, file_data"
            ).eq("id", consent_id).execute()

            if not response.data or not response.data[0].get("file_data"):
                raise HTTPException(404, "No scanned copy stored for this consent.")

            row = response.data[0]
            return Response(
                content=row["file_data"],
                media_type="application/pdf",
                headers={
                    "Content-Disposition": f'attachment; filename="{row["file_name"]}"'
                },
            )
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error downloading consent file: {e}")
        raise HTTPException(500, "Error downloading file")


@router.post("/volunteers/resources")
async def add_resource(
    volunteer: Volunteer = None,
    title: str = Form(...),
    url: str = Form(...),
    description: str = Form(""),
    category: str = Form("general"),
):
    try:
        with db() as supabase:
            supabase.table("teaching_resources").insert(
                {
                    "title": title,
                    "description": description,
                    "url": url,
                    "category": category,
                    "added_by": volunteer["email"],
                }
            ).execute()
    except Exception as e:
        print(f"Error adding resource: {e}")
        raise HTTPException(500, "Error adding resource")
    return RedirectResponse("/volunteers", status_code=303)
