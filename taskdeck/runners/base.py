"""Agent runner interface.

A runner *executes* a task card (vs. the core, where a human moves cards by
hand). Runners are optional and opt-in via `TASKDECK_RUNNER`; the core never
depends on one. Implementations: `echo` (built-in, synchronous, for tests/demos)
and, from step 4, `claude` (subprocess to the Claude CLI).

Each method receives and returns the task dict. A runner is given the store so an
asynchronous implementation can persist later state transitions on its own; the
synchronous echo runner persists inline and returns the updated task.
"""
from __future__ import annotations

import abc
from typing import Any, Dict


class Runner(abc.ABC):
    def __init__(self, store, config) -> None:
        self.store = store
        self.config = config

    @abc.abstractmethod
    def run(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Begin executing `task`. Returns the task with run state advanced."""

    @abc.abstractmethod
    def instruct(self, task: Dict[str, Any], message: str) -> Dict[str, Any]:
        """Feed a user answer to a task that is awaiting input, and resume."""

    @abc.abstractmethod
    def abort(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Stop a task and mark it aborted."""
