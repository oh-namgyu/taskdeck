"""Store package: factory that selects a backend from config."""
from __future__ import annotations

from .base import Store
from .sqlite_store import SqliteStore

__all__ = ["Store", "SqliteStore", "get_store"]


def get_store(config) -> Store:
    """Return the configured store. v1 ships SQLite only."""
    return SqliteStore(config.db_path)
