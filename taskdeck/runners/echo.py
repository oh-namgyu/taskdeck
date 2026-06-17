"""Built-in synchronous runner used for tests and demos.

It does no real work: it "executes" a card by echoing its body, completing
immediately into the Review column. It exercises the runner wiring and the run
endpoints without any external dependency. The Claude CLI runner implements the
same interface asynchronously.
"""
from __future__ import annotations

from typing import Any, Dict

from ..models import now_iso
from .base import Runner


def _record(output: str, message: str) -> Dict[str, Any]:
    ts = now_iso()
    return {
        "started_at": ts,
        "ended_at": ts,
        "last_message": message,
        "full_output": output,
        "question": None,
        "exit_code": 0,
    }


class EchoRunner(Runner):
    def run(self, task):
        source = task.get("body") or task["title"]
        output = "echo: " + source
        task["run"] = _record(output, output)
        task["run_status"] = "awaiting_review"
        task["status"] = "review"
        return self.store.update_task(task)

    def instruct(self, task, message):
        prev = (task.get("run") or {}).get("full_output", "")
        output = prev + "\n> " + message + "\necho: " + message
        task["run"] = _record(output, "echo: " + message)
        task["run_status"] = "awaiting_review"
        task["status"] = "review"
        return self.store.update_task(task)

    def abort(self, task):
        task["run_status"] = "aborted"
        task["status"] = "review"
        return self.store.update_task(task)
