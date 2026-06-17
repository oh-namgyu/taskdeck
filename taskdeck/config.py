"""Runtime configuration, sourced entirely from environment variables.

No hardcoded paths or host-specific values: a clean checkout runs anywhere.
"""
from __future__ import annotations

import os
import shutil


class Config:
    """Holds the knobs the app, store and runner need. Construct once per app."""

    def __init__(self) -> None:
        self.host = os.environ.get("TASKDECK_HOST", "127.0.0.1")
        self.port = int(os.environ.get("TASKDECK_PORT", "6090"))
        self.data_dir = os.environ.get("TASKDECK_DATA", "./data")
        # "none" keeps the agent runner (and its endpoints) disabled.
        self.runner = os.environ.get("TASKDECK_RUNNER", "none")

        # --- agent runner (only used when runner != none) ---
        self.claude_bin = (
            os.environ.get("TASKDECK_CLAUDE_BIN")
            or os.environ.get("CLAUDE_BIN")
            or shutil.which("claude")
            or "claude"
        )
        self.run_cwd = (
            os.environ.get("TASKDECK_RUN_CWD")
            or os.path.join(self.data_dir, "workspace")
        )
        self.run_timeout = int(os.environ.get("TASKDECK_RUN_TIMEOUT", "600"))
        self.run_maxbytes = int(os.environ.get("TASKDECK_RUN_MAXBYTES", "100000"))

        # Optional shared secret; when set, mutating/run requests must carry it
        # in the X-TaskDeck-Token header.
        self.token = os.environ.get("TASKDECK_TOKEN") or ""

    @property
    def db_path(self) -> str:
        return os.path.join(self.data_dir, "taskdeck.db")
