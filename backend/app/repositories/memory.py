"""In-memory document store for local development and tests.

Thread-safe and deep-copying, so callers cannot mutate stored state by holding
on to a returned dict.
"""

from __future__ import annotations

import copy
import threading
from collections import defaultdict

from app.repositories.base import DocumentStore


class InMemoryDocumentStore(DocumentStore):
    def __init__(self) -> None:
        self._data: dict[str, dict[str, dict]] = defaultdict(dict)
        self._lock = threading.RLock()

    def get(self, collection: str, doc_id: str) -> dict | None:
        with self._lock:
            raw = self._data[collection].get(doc_id)
            return copy.deepcopy(raw) if raw is not None else None

    def list(self, collection: str) -> list[dict]:
        with self._lock:
            return [copy.deepcopy(value) for value in self._data[collection].values()]

    def set(self, collection: str, doc_id: str, data: dict) -> None:
        with self._lock:
            self._data[collection][doc_id] = copy.deepcopy(data)

    def delete(self, collection: str, doc_id: str) -> None:
        with self._lock:
            self._data[collection].pop(doc_id, None)

    def clear(self, collection: str) -> None:
        with self._lock:
            self._data[collection] = {}

    def clear_all(self) -> None:
        with self._lock:
            self._data.clear()
