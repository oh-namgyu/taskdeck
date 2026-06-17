"""Task data model: schema, enums, validation and builders.

Validation lives here (not in the store or the API) so every entry point shares
one definition of a valid task. Storage stays a dumb persistence layer.
"""
from __future__ import annotations

import threading
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

SCHEMA_VERSION = 1

STATUSES = ("todo", "doing", "review", "done")
RUN_STATUSES = (
    "none", "running", "awaiting_user",
    "awaiting_review", "failed", "aborted", "completed",
)

# Fields a client may set when creating or updating a task. run_status / run are
# owned by the agent runner (step 3-4), never set directly by the API client.
_WRITABLE = ("title", "body", "status", "project", "due_date", "tags")

# Max lengths for free-text fields (reject oversized input rather than store it).
_MAX_LEN = {"title": 1000, "body": 50000, "project": 200, "due_date": 64, "tag": 100}

_id_lock = threading.Lock()
_last_id = 0


class ValidationError(ValueError):
    """Incoming task data violates the contract -> HTTP 400."""


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def new_id() -> int:
    """Monotonic, collision-free epoch-millisecond id (safe for rapid creates)."""
    global _last_id
    with _id_lock:
        candidate = int(time.time() * 1000)
        if candidate <= _last_id:
            candidate = _last_id + 1
        _last_id = candidate
        return candidate


def _coerce_str(value: Any, field: str, required: bool = False) -> Optional[str]:
    """Validate an optional/required string field; trims and length-checks it."""
    if value is None or (isinstance(value, str) and not value.strip() and required):
        if required:
            raise ValidationError("%s is required" % field)
        return None
    if not isinstance(value, str):
        raise ValidationError("%s must be a string" % field)
    text = value.strip()
    if len(text) > _MAX_LEN.get(field, 10000):
        raise ValidationError("%s is too long (max %d)" % (field, _MAX_LEN[field]))
    return text


def _norm_tags(tags: Any) -> List[str]:
    if tags is None:
        return []
    if not isinstance(tags, list) or any(not isinstance(t, str) for t in tags):
        raise ValidationError("tags must be a list of strings")
    if any(len(t) > _MAX_LEN["tag"] for t in tags):
        raise ValidationError("a tag is too long (max %d)" % _MAX_LEN["tag"])
    return tags


def _validate_status(status: Any) -> str:
    if status not in STATUSES:
        raise ValidationError("status must be one of %s" % (STATUSES,))
    return status


def build_task(data: Dict[str, Any]) -> Dict[str, Any]:
    """Build a complete task record from client create data."""
    ts = now_iso()
    return {
        "id": new_id(),
        "title": _coerce_str(data.get("title"), "title", required=True),
        "body": _coerce_str(data.get("body"), "body") or "",
        "status": _validate_status(data.get("status", "todo")),
        "project": _coerce_str(data.get("project"), "project"),
        "due_date": _coerce_str(data.get("due_date"), "due_date"),
        "tags": _norm_tags(data.get("tags")),
        "run_status": "none",
        "run": None,
        "created_at": ts,
        "updated_at": ts,
        "schema_version": SCHEMA_VERSION,
    }


def apply_patch(task: Dict[str, Any], patch: Dict[str, Any]) -> Dict[str, Any]:
    """Return a copy of `task` with the writable fields in `patch` applied."""
    updated = dict(task)
    for key in _WRITABLE:
        if key not in patch:
            continue
        if key == "title":
            updated["title"] = _coerce_str(patch.get("title"), "title", required=True)
        elif key == "status":
            updated["status"] = _validate_status(patch["status"])
        elif key == "tags":
            updated["tags"] = _norm_tags(patch.get("tags"))
        else:  # body, project, due_date
            updated[key] = _coerce_str(patch.get(key), key)
    updated["updated_at"] = now_iso()
    return updated
