"""TaskDeck application factory.

Core only: task CRUD + health. The agent runner and its endpoints
(`/api/tasks/<id>/run` …) are mounted in a later step and stay 404 while
`TASKDECK_RUNNER=none`.
"""
from __future__ import annotations

import os
from typing import Optional

from flask import Flask

from .config import Config
from .store import get_store

__all__ = ["create_app", "Config"]


def create_app(config: Optional[Config] = None) -> Flask:
    config = config or Config()
    os.makedirs(config.data_dir, exist_ok=True)

    # Default static folder is the package's `static/` dir, served at /static.
    app = Flask(__name__)
    app.config["TASKDECK"] = config
    app.config["STORE"] = get_store(config)

    from .api.tasks import bp as tasks_bp
    app.register_blueprint(tasks_bp)

    @app.get("/")
    def index():
        return app.send_static_file("index.html")

    @app.get("/api/health")
    def health():
        return {"status": "ok", "runner": config.runner}

    return app
