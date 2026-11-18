from datetime import UTC, datetime
from typing import Any

from supabase import create_client, Client

from .config import SUPABASE_URL, SUPABASE_KEY
from .passwords import pwd_context

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


class Database:
    """Context manager for database operations with Supabase."""

    def __init__(self):
        self.client = supabase

    def __enter__(self):
        return self.client

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


def db() -> Database:
    """Return a database context manager."""
    return Database()


def init_db() -> None:
    """Initialize database with seed data for teaching_resources and admin user."""
    # Seed teaching_resources if empty
    try:
        response = supabase.table("teaching_resources").select("id", count="exact").execute()
        if response.count == 0:
            seed = [
                {
                    "title": "micro:bit Get Started",
                    "description": "Official first-lessons guide for new clubs.",
                    "url": "https://microbit.org/get-started/",
                    "category": "session-plan",
                },
                {
                    "title": "MakeCode micro:bit editor",
                    "description": "Block-coding editor we use in sessions 1-8.",
                    "url": "https://makecode.microbit.org/",
                    "category": "microbit",
                },
                {
                    "title": "micro:bit Python Editor (V3)",
                    "description": "Browser-based MicroPython editor for the transition term.",
                    "url": "https://python.microbit.org/v/3",
                    "category": "python",
                },
                {
                    "title": "micro:bit Projects & Ideas",
                    "description": "Curated project ideas by difficulty.",
                    "url": "https://microbit.org/projects/make-it/",
                    "category": "microbit",
                },
                {
                    "title": "Code & AI with the micro:bit",
                    "description": "Foundation activities introducing AI concepts safely.",
                    "url": "https://microbit.org/code-ai/",
                    "category": "safety",
                },
                {
                    "title": "BBC micro:bit lessons",
                    "description": "Full lesson sequences mapped to the curriculum.",
                    "url": "https://microbit.org/lessons/",
                    "category": "session-plan",
                },
            ]
            supabase.table("teaching_resources").insert(seed).execute()
    except Exception as e:
        print(f"Error seeding teaching_resources: {e}")

    # Seed admin volunteer if none exist
    try:
        response = supabase.table("volunteers").select("id", count="exact").execute()
        if response.count == 0:
            supabase.table("volunteers").insert(
                {
                    "email": "admin@yourcodeclub.org.uk",
                    "name": "Club Admin",
                    "password_hash": pwd_context.hash("change-me-now"),
                    "is_admin": True,
                    "auth_provider": "password",
                    "created_at": datetime.now(UTC).isoformat(),
                }
            ).execute()
    except Exception as e:
        print(f"Error seeding admin volunteer: {e}")

