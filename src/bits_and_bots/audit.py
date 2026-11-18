"""Minimal audit events: metadata only, never form contents or sensitive notes."""

from datetime import UTC, datetime
from typing import Any

from .database import db


def record_event(
    *,
    actor_id: str | int | None,
    action: str,
    resource_type: str,
    resource_id: str | int | None = None,
    outcome: str = "success",
    request_id: str | None = None,
) -> None:
    event: dict[str, Any] = {
        "actor_id": str(actor_id) if actor_id is not None else None,
        "action": action,
        "resource_type": resource_type,
        "resource_id": str(resource_id) if resource_id is not None else None,
        "outcome": outcome,
        "request_id": request_id,
        "created_at": datetime.now(UTC).isoformat(),
    }
    # Do not silently pretend an audit write succeeded. Callers handling sensitive
    # state changes should fail closed if the audit store is unavailable.
    with db() as client:
        client.table("audit_events").insert(event).execute()
