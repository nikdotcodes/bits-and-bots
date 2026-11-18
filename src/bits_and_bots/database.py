"""Lazy Supabase client access. Importing the app never contacts the database."""
from contextlib import contextmanager
from functools import lru_cache

from supabase import Client, create_client

from .config import SUPABASE_KEY, SUPABASE_URL


@lru_cache(maxsize=1)
def get_client() -> Client:
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise RuntimeError("Supabase is not configured; set SUPABASE_URL and SUPABASE_KEY")
    return create_client(SUPABASE_URL, SUPABASE_KEY)


@contextmanager
def db():
    """Yield the server-side Supabase client."""
    yield get_client()


def init_db() -> None:
    """Intentionally does not seed privileged accounts or mutate production data.

    Apply version-controlled SQL migrations separately and provision the first
    administrator using the documented one-time bootstrap procedure.
    """
    return None
