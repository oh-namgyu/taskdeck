"""Storage interface.

Implementations persist task dicts (already built/validated by `models`). v1 ships
a single SQLite-backed store; the interface leaves room for alternatives.
"""
from __future__ import annotations

import abc
from typing import Any, Dict, List, Optional


class Store(abc.ABC):
    @abc.abstractmethod
    def list_tasks(
        self,
        *,
        date: Optional[str] = None,
        project: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        ...

    @abc.abstractmethod
    def get_task(self, task_id: int) -> Optional[Dict[str, Any]]:
        ...

    @abc.abstractmethod
    def create_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        ...

    @abc.abstractmethod
    def update_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        ...

    @abc.abstractmethod
    def delete_task(self, task_id: int) -> bool:
        ...

    def close(self) -> None:  # pragma: no cover - optional override
        pass
