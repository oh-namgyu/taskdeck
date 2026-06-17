"""Request guard for state-changing requests.

TaskDeck binds to loopback by default and is a single-user local tool, but a
local web app that can launch an agent CLI is a real CSRF / DNS-rebinding
target: any web page open in the same browser could POST to localhost. So:

- **Origin/Referer check** — browsers always send `Origin` on cross-origin
  state-changing requests; if present and it does not match our own host, the
  request is rejected. Absent (non-browser clients like curl) is allowed, which
  is safe because those are not the CSRF threat.
- **Token gate (optional)** — if `TASKDECK_TOKEN` is set, every mutating/run
  request must carry it in `X-TaskDeck-Token`. Defence in depth, also covers
  non-browser clients.

Only unsafe methods are guarded; GET/HEAD (board, static assets, listing) pass
through untouched.
"""
from __future__ import annotations

from urllib.parse import urlparse

from flask import jsonify, request

_UNSAFE = {"POST", "PUT", "PATCH", "DELETE"}


def install_request_guard(app, config) -> None:
    token = config.token

    @app.before_request
    def _guard():
        if request.method not in _UNSAFE:
            return None
        if token and request.headers.get("X-TaskDeck-Token") != token:
            return jsonify({"error": "invalid or missing token"}), 403
        source = request.headers.get("Origin") or request.headers.get("Referer")
        if source:
            netloc = urlparse(source).netloc
            if netloc and netloc != request.host:
                return jsonify({"error": "cross-origin request blocked"}), 403
        return None
