import os
import secrets


import sqlite3
from supabase import create_client

from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-change-me-" + secrets.token_hex(16))
DB_PATH = os.getenv("DB_PATH", "codeclub.db")
BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8000")

# Supabase configuration (use new API keys format)
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")  # Either publishable or secret key



# Connect to both databases
sqlite_conn = sqlite3.connect(DB_PATH)
sqlite_conn.row_factory = sqlite3.Row
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Migrate volunteers
volunteers = sqlite_conn.execute("SELECT * FROM volunteers").fetchall()
for vol in volunteers:
    supabase.table("volunteers").insert({
        "id": vol["id"],  # Preserve IDs
        "email": vol["email"],
        "name": vol["name"],
        "password_hash": vol["password_hash"],
        "is_admin": bool(vol["is_admin"]),
        "auth_provider": vol["auth_provider"],
        "created_at": vol["created_at"],
    }).execute()

# Migrate contact messages
messages = sqlite_conn.execute("SELECT * FROM contact_messages").fetchall()
for msg in messages:
    supabase.table("contact_messages").insert({
        "id": msg["id"],
        "name": msg["name"],
        "email": msg["email"],
        "phone": msg["phone"],
        "child_year_group": msg["child_year_group"],
        "message": msg["message"],
        "created_at": msg["created_at"],
    }).execute()

# Migrate consent submissions
consents = sqlite_conn.execute("SELECT * FROM consent_submissions").fetchall()
for consent in consents:
    supabase.table("consent_submissions").insert({
        "id": consent["id"],
        "child_first_name": consent["child_first_name"],
        "child_last_initial": consent["child_last_initial"],
        "child_year_group": consent["child_year_group"],
        "parent_name": consent["parent_name"],
        "parent_email": consent["parent_email"],
        "parent_phone": consent["parent_phone"],
        "emergency_contact": consent["emergency_contact"],
        "medical_notes": consent["medical_notes"],
        "ai_tools_consent": consent["ai_tools_consent"],
        "signature_name": consent["signature_name"],
        "signed_date": consent["signed_date"],
        "status": consent["status"],
        "signed_off_by": consent["signed_off_by"],
        "signed_off_at": consent["signed_off_at"],
        "file_name": consent["file_name"],
        "file_data": consent["file_data"],
        "created_at": consent["created_at"],
    }).execute()

# Migrate teaching resources
resources = sqlite_conn.execute("SELECT * FROM teaching_resources").fetchall()
for res in resources:
    supabase.table("teaching_resources").insert({
        "id": res["id"],
        "title": res["title"],
        "description": res["description"],
        "url": res["url"],
        "category": res["category"],
        "added_by": res["added_by"],
    }).execute()

sqlite_conn.close()
print("Migration complete!")