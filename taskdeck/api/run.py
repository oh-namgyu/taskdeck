"""Runner endpoints. Mounted only when a runner is enabled (see app factory),
so with TASKDECK_RUNNER=none these paths return 404.

Contract (plan §4-API):
  POST /api/tasks/<id>/run       202  | 404 | 409 already running
  POST /api/tasks/<id>/instruct  200  | 404 | 409 not awaiting user | 400 no message
  POST /api/tasks/<id>/complete  200  | 404 | 409 no finished run
  POST /api/tasks/<id>/abort     200  | 404 | 409 not running
"""
from __future__ import annotations

from flask import Blueprint, current_app, jsonify, request

bp = Blueprint("run", __name__)


def _store():
    return current_app.config["STORE"]


def _runner():
    return current_app.config["RUNNER"]


def _error(message, code):
    return jsonify({"error": message}), code


def _load(task_id):
    """Return (task, None) or (None, error_response)."""
    task = _store().get_task(task_id)
    if task is None:
        return None, _error("task not found", 404)
    return task, None


@bp.post("/api/tasks/<int:task_id>/run")
def run_task(task_id):
    task, err = _load(task_id)
    if err:
        return err
    if task.get("run_status") == "running":
        return _error("task is already running", 409)
    return jsonify({"task": _runner().run(task)}), 202


@bp.post("/api/tasks/<int:task_id>/instruct")
def instruct_task(task_id):
    task, err = _load(task_id)
    if err:
        return err
    if task.get("run_status") != "awaiting_user":
        return _error("task is not awaiting user input", 409)
    message = ((request.get_json(silent=True) or {}).get("message") or "").strip()
    if not message:
        return _error("message is required", 400)
    return jsonify({"task": _runner().instruct(task, message)})


@bp.post("/api/tasks/<int:task_id>/complete")
def complete_task(task_id):
    task, err = _load(task_id)
    if err:
        return err
    if task.get("run_status") in ("none", "running"):
        return _error("task has no finished run to complete", 409)
    task["status"] = "done"
    task["run_status"] = "completed"
    return jsonify({"task": _store().update_task(task)})


@bp.post("/api/tasks/<int:task_id>/abort")
def abort_task(task_id):
    task, err = _load(task_id)
    if err:
        return err
    if task.get("run_status") not in ("running", "awaiting_user"):
        return _error("task is not running", 409)
    return jsonify({"task": _runner().abort(task)})
