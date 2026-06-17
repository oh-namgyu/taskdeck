"""Task CRUD API. Contract documented in the README.

The store is resolved from the app config per request, so tests can inject a
temporary database via the app factory.
"""
from __future__ import annotations

from flask import Blueprint, current_app, jsonify, request

from ..models import ValidationError, apply_patch, build_task

bp = Blueprint("tasks", __name__)


def _store():
    return current_app.config["STORE"]


@bp.get("/api/tasks")
def list_tasks():
    args = request.args
    tasks = _store().list_tasks(
        date=args.get("date"),
        project=args.get("project"),
        status=args.get("status"),
    )
    return jsonify({"tasks": tasks})


@bp.post("/api/tasks")
def create_task():
    data = request.get_json(silent=True) or {}
    try:
        task = build_task(data)
    except ValidationError as exc:
        return jsonify({"error": str(exc)}), 400
    _store().create_task(task)
    return jsonify({"task": task}), 201


@bp.put("/api/tasks/<int:task_id>")
def update_task(task_id):
    data = request.get_json(silent=True) or {}
    store = _store()
    existing = store.get_task(task_id)
    if existing is None:
        return jsonify({"error": "task not found"}), 404
    try:
        updated = apply_patch(existing, data)
    except ValidationError as exc:
        return jsonify({"error": str(exc)}), 400
    store.update_task(updated)
    return jsonify({"task": updated})


@bp.delete("/api/tasks/<int:task_id>")
def delete_task(task_id):
    if not _store().delete_task(task_id):
        return jsonify({"error": "task not found"}), 404
    return "", 204
