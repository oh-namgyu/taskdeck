"""Runner registry and factory.

`TASKDECK_RUNNER=none` (default) disables runners entirely: `get_runner` returns
None and the run endpoints are never mounted. Any other value must name a known
runner.
"""
from __future__ import annotations

from typing import Optional

from .base import Runner

__all__ = ["Runner", "get_runner"]


def _registry():
    # Imported lazily so the core never imports runner implementations unless one
    # is actually requested.
    from .echo import EchoRunner
    return {"echo": EchoRunner}


def get_runner(config, store) -> Optional[Runner]:
    name = (config.runner or "none").strip().lower()
    if name == "none":
        return None
    registry = _registry()
    if name not in registry:
        available = ", ".join(sorted(registry)) or "(none)"
        raise ValueError(
            "unknown TASKDECK_RUNNER %r (available: %s)" % (name, available)
        )
    return registry[name](store, config)
