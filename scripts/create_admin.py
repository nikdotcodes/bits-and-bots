"""One-time, operator-run initial administrator provisioning.

Run only after applying the Supabase production migration:
    uv run python scripts/create_admin.py
"""
from getpass import getpass
import re

from bits_and_bots.audit import record_event
from bits_and_bots.config import validate_config
from bits_and_bots.database import db
from bits_and_bots.passwords import hash_password


def main() -> None:
    validate_config()
    email = input("Administrator email: ").strip().lower()
    name = input("Administrator display name: ").strip()
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        raise SystemExit("A valid email address is required.")
    if not name or len(name) > 160:
        raise SystemExit("A display name between 1 and 160 characters is required.")
    password = getpass("Initial password (12+ characters): ")
    confirmation = getpass("Confirm password: ")
    if password != confirmation or len(password) < 12:
        raise SystemExit("Passwords must match and contain at least 12 characters.")

    with db() as client:
        existing = client.table("volunteers").select("id").eq(
            "email", email
        ).limit(1).execute()
        if existing.data:
            raise SystemExit("An account with that email already exists.")
        result = client.table("volunteers").insert({
            "email": email,
            "name": name,
            "password_hash": hash_password(password),
            "is_admin": True,
            "auth_provider": "password",
        }).execute()
        if not result.data:
            raise SystemExit("Administrator creation did not return a record.")
        admin_id = result.data[0]["id"]
        record_event(
            actor_id=admin_id, action="admin.bootstrap",
            resource_type="volunteer", resource_id=admin_id,
        )
    print("Initial administrator created. Store the credentials in your password manager.")


if __name__ == "__main__":
    main()
