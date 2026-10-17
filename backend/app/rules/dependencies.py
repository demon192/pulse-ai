"""Task dependency traversal.

``Task.dependency_ids`` points at the tasks that must finish first, so the
"downstream" direction (work waiting on a task) is the reverse edge.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Iterable

from app.schemas.domain import Task


class DependencyGraph:
    def __init__(self, tasks: Iterable[Task]) -> None:
        self._tasks: dict[str, Task] = {task.id: task for task in tasks}
        self._dependents: dict[str, list[str]] = {task_id: [] for task_id in self._tasks}
        for task in self._tasks.values():
            for dependency_id in task.dependency_ids:
                # Tolerate dangling references rather than failing the dashboard.
                if dependency_id in self._dependents:
                    self._dependents[dependency_id].append(task.id)

    @property
    def tasks(self) -> dict[str, Task]:
        return self._tasks

    def get(self, task_id: str) -> Task | None:
        return self._tasks.get(task_id)

    def direct_dependents(self, task_id: str) -> list[Task]:
        """Tasks that directly wait on ``task_id``."""
        return [self._tasks[dep] for dep in self._dependents.get(task_id, [])]

    def direct_dependencies(self, task_id: str) -> list[Task]:
        task = self._tasks.get(task_id)
        if task is None:
            return []
        return [
            self._tasks[dependency_id]
            for dependency_id in task.dependency_ids
            if dependency_id in self._tasks
        ]

    def downstream(self, task_id: str, *, include_completed: bool = False) -> list[Task]:
        """All tasks transitively waiting on ``task_id`` (breadth-first).

        Cycle-safe: each task is visited at most once.
        """
        seen: set[str] = {task_id}
        queue: deque[str] = deque(self._dependents.get(task_id, []))
        result: list[Task] = []
        while queue:
            current = queue.popleft()
            if current in seen:
                continue
            seen.add(current)
            task = self._tasks.get(current)
            if task is None:
                continue
            if include_completed or task.is_open:
                result.append(task)
            queue.extend(self._dependents.get(current, []))
        return result

    def upstream(self, task_id: str) -> list[Task]:
        """All tasks ``task_id`` transitively depends on."""
        seen: set[str] = {task_id}
        start = self._tasks.get(task_id)
        if start is None:
            return []
        queue: deque[str] = deque(start.dependency_ids)
        result: list[Task] = []
        while queue:
            current = queue.popleft()
            if current in seen:
                continue
            seen.add(current)
            task = self._tasks.get(current)
            if task is None:
                continue
            result.append(task)
            queue.extend(task.dependency_ids)
        return result

    def blocking_dependencies(self, task_id: str) -> list[Task]:
        """Direct dependencies that are not yet complete."""
        return [task for task in self.direct_dependencies(task_id) if task.is_open]

    def downstream_task_ids(self, task_ids: Iterable[str]) -> list[str]:
        """Union of downstream ids for several tasks, excluding the inputs."""
        source = set(task_ids)
        collected: dict[str, None] = {}
        for task_id in source:
            for task in self.downstream(task_id):
                if task.id not in source:
                    collected[task.id] = None
        return list(collected)
