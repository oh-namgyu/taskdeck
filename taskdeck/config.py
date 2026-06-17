"""Runtime configuration, sourced entirely from environment variables.

No hardcoded paths or host-specific values: a clean checkout runs anywhere.
"""
from __future__ import annotations

import os


class Config:
    """Holds the knobs the app and store need. Construct once per app."""

    def __init__(self) -> None:
        self.host = os.environ.get("TASKDECK_HOST", "127.0.0.1")
        self.port = int(os.environ.get("TASKDECK_PORT", "6090"))
        self.data_dir = os.environ.get("TASKDECK_DATA", "./data")
        # "none" keeps the agent runner (and its endpoints) disabled.
        self.runner = os.environ.get("TASKDECK_RUNNER", "none")

    @property
    def db_path(self) -> str:
        return os.path.join(self.data_dir, "taskdeck.db")
