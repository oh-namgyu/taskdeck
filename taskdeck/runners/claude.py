"""Experimental Claude CLI runner.

Executes a task by invoking the Claude CLI as a background subprocess and
streaming the result back into the task's run state. This is the one place
TaskDeck shells out to an external program, so it is hardened accordingly:

- `shell=False` with an argument array (no shell interpolation of task text)
- a fixed, realpath-checked working directory that refuses sensitive locations
- a hard timeout that terminates the whole process group (no orphans)
- a cap on captured output size

The subprocess inherits the server's environment, because it runs the user's own
CLI, which needs that context (e.g. its credentials) exactly as if the user ran
it by hand. Isolate with a container, not an env filter (see SECURITY.md).

It is opt-in (`TASKDECK_RUNNER=claude`) and disabled by default. As a public,
self-contained project this intentionally calls the CLI directly rather than
through any private gateway.

Each run is tagged with a monotonic generation. A worker thread only writes its
result back if its generation is still the active one for the task; `abort` (and
a superseding run) drops the generation, so a late-finishing or killed worker can
never overwrite an aborted/newer state.
"""
from __future__ import annotations

import os
import signal
import subprocess
import threading
from typing import Dict, Optional, Tuple

from ..models import now_iso
from .base import Runner

_PROMPT_PREFIX = (
    "You are completing a task from a kanban board. Work on it directly. "
    "If you need information from the user before you can finish, end your reply "
    "with a single final line of the form: [QUESTION] <your question>\n\nTask: "
)

_QUESTION_MARKER = "[QUESTION]"

_SENSITIVE_DIRS = ("/", "/etc", "/usr", "/bin", "/sbin", "/var", "/root")


class RunnerError(RuntimeError):
    pass


def _runner_env() -> Dict[str, str]:
    # Inherit the server's environment so the user's CLI has its usual context
    # (notably its auth). Isolation is the container's job, not an env filter.
    return dict(os.environ)


def _parse_question(output: str) -> Optional[str]:
    for line in reversed((output or "").strip().splitlines()):
        line = line.strip()
        if line.startswith(_QUESTION_MARKER):
            return line[len(_QUESTION_MARKER):].strip() or None
    return None


def _last_line(output: str) -> str:
    lines = [ln for ln in (output or "").splitlines() if ln.strip()]
    return lines[-1][:300] if lines else ""


def _terminate(proc: subprocess.Popen) -> None:
    """Kill the whole process group so no child is orphaned."""
    for sig in (signal.SIGTERM, signal.SIGKILL):
        if proc.poll() is not None:
            return
        try:
            os.killpg(os.getpgid(proc.pid), sig)
        except (ProcessLookupError, PermissionError):
            return
        try:
            proc.wait(timeout=5)
            return
        except subprocess.TimeoutExpired:
            continue


class ClaudeRunner(Runner):
    def __init__(self, store, config) -> None:
        super().__init__(store, config)
        self._procs: Dict[int, subprocess.Popen] = {}
        self._active: Dict[int, int] = {}  # task_id -> current run generation
        self._counter = 0
        self._lock = threading.Lock()
        self._cwd = self._resolve_cwd()

    def _resolve_cwd(self) -> str:
        # Exact-match check only: rejecting whole subtrees would also reject
        # legitimate temp/data dirs (e.g. macOS tmp lives under /private/var).
        root = os.path.realpath(self.config.run_cwd)
        sensitive = {os.path.realpath(p) for p in _SENSITIVE_DIRS}
        sensitive.add(os.path.realpath(os.path.expanduser("~")))
        if root in sensitive:
            raise RunnerError("refusing to run in sensitive directory: %s" % root)
        os.makedirs(root, exist_ok=True)
        return root

    # --- Runner interface ---
    def run(self, task):
        return self._launch(task, _PROMPT_PREFIX + (task.get("body") or task["title"]))

    def instruct(self, task, message):
        return self._launch(task, self._compose_instruct(task, message))

    def abort(self, task):
        tid = task["id"]
        with self._lock:
            # Drop the active generation so the worker's _finish (after the kill)
            # cannot overwrite the aborted state, regardless of timing.
            self._active.pop(tid, None)
            proc = self._procs.get(tid)
        if proc is not None:
            _terminate(proc)
        task["run_status"] = "aborted"
        task["status"] = "review"
        return self.store.update_task(task)

    # --- internals ---
    def _compose_instruct(self, task, message: str) -> str:
        body = task.get("body") or task["title"]
        prev = (task.get("run") or {}).get("full_output", "")
        return (_PROMPT_PREFIX + body
                + "\n\n--- previous output ---\n" + prev[-2000:]
                + "\n\n--- user answer ---\n" + message)

    def _launch(self, task, prompt: str):
        tid = task["id"]
        with self._lock:
            if tid in self._active:
                # Already running (e.g. a duplicate concurrent request): no-op,
                # don't spawn a second, untracked subprocess.
                return self.store.get_task(tid) or task
            self._counter += 1
            gen = self._counter
            self._active[tid] = gen
        task["run_status"] = "running"
        task["status"] = "doing"
        task["run"] = {"started_at": now_iso(), "ended_at": None,
                       "last_message": "", "full_output": "",
                       "question": None, "exit_code": None}
        self.store.update_task(task)
        thread = threading.Thread(
            target=self._execute, args=(tid, gen, prompt), daemon=True)
        thread.start()
        return task

    def _execute(self, task_id: int, gen: int, prompt: str) -> None:
        try:
            output, code, timed_out = self._spawn(task_id, prompt)
        except Exception as exc:  # noqa: BLE001 - surface any failure as run state
            self._finish(task_id, gen, "failed", str(exc), None)
            return
        if timed_out:
            self._finish(task_id, gen, "failed", output + "\n[timeout]", None)
            return
        if code != 0:
            # e.g. the CLI errored or isn't authenticated; surface it as failed
            # rather than letting a non-zero run masquerade as awaiting_review.
            self._finish(task_id, gen, "failed", output, code)
            return
        question = _parse_question(output)
        status = "awaiting_user" if question else "awaiting_review"
        self._finish(task_id, gen, status, output, code, question)

    def _spawn(self, task_id: int, prompt: str) -> Tuple[str, Optional[int], bool]:
        proc = subprocess.Popen(
            [self.config.claude_bin, "-p", prompt],
            cwd=self._cwd, env=_runner_env(),
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, text=True, start_new_session=True,
        )
        with self._lock:
            self._procs[task_id] = proc
        timed_out = False
        try:
            output, _ = proc.communicate(timeout=self.config.run_timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            _terminate(proc)
            output, _ = proc.communicate()
        finally:
            with self._lock:
                if self._procs.get(task_id) is proc:
                    self._procs.pop(task_id, None)
        capped = (output or "")[: self.config.run_maxbytes]
        return capped, proc.returncode, timed_out

    def _finish(self, task_id: int, gen: int, run_status: str, output: str,
                code: Optional[int], question: Optional[str] = None) -> None:
        with self._lock:
            if self._active.get(task_id) != gen:
                return  # aborted or superseded by a newer run; don't overwrite
            self._active.pop(task_id, None)  # this run is complete
        task = self.store.get_task(task_id)
        if task is None:
            return
        run = task.get("run") or {}
        run.update({
            "ended_at": now_iso(),
            "full_output": (output or "")[: self.config.run_maxbytes],
            "last_message": _last_line(output),
            "question": question,
            "exit_code": code,
        })
        task["run"] = run
        task["run_status"] = run_status
        task["status"] = "doing" if run_status == "awaiting_user" else "review"
        self.store.update_task(task)
