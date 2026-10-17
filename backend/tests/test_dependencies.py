"""Dependency traversal."""

from __future__ import annotations

from app.rules.dependencies import DependencyGraph
from app.schemas.domain import Task


def _task(task_id: str, deps: list[str]) -> Task:
    return Task(
        id=task_id,
        project_id="p1",
        title=task_id,
        description="",
        dependency_ids=deps,
    )


def test_downstream_is_transitive():
    graph = DependencyGraph(
        [_task("a", []), _task("b", ["a"]), _task("c", ["b"]), _task("d", ["c"])]
    )
    assert {task.id for task in graph.downstream("a")} == {"b", "c", "d"}
    assert graph.downstream("d") == []


def test_cycles_do_not_hang():
    graph = DependencyGraph([_task("a", ["b"]), _task("b", ["a"])])
    assert {task.id for task in graph.downstream("a")} == {"b"}
    assert {task.id for task in graph.upstream("a")} == {"b"}


def test_dangling_dependency_is_tolerated():
    graph = DependencyGraph([_task("a", ["does-not-exist"])])
    assert graph.direct_dependencies("a") == []
    assert graph.blocking_dependencies("a") == []


def test_downstream_ids_excludes_the_inputs(database):
    graph = DependencyGraph(database.tasks.list_all())
    ids = graph.downstream_task_ids(["pay-01", "pay-02"])
    assert "pay-03" in ids
    assert "pay-01" not in ids and "pay-02" not in ids
