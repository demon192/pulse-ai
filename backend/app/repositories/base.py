"""Storage abstraction.

The application never talks to Firestore directly. It talks to typed
repositories backed by a :class:`DocumentStore`, which has an in-memory
implementation for local development and tests and a Firestore implementation
for deployment.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable, Iterable
from typing import Generic, TypeVar

from pydantic import BaseModel

ModelT = TypeVar("ModelT", bound=BaseModel)


class EntityNotFound(LookupError):
    """Raised when a repository lookup for a required entity fails."""

    def __init__(self, collection: str, doc_id: str) -> None:
        super().__init__(f"{collection}/{doc_id} not found")
        self.collection = collection
        self.doc_id = doc_id


class DocumentStore(ABC):
    """A minimal document database interface."""

    @abstractmethod
    def get(self, collection: str, doc_id: str) -> dict | None: ...

    @abstractmethod
    def list(self, collection: str) -> list[dict]: ...

    @abstractmethod
    def set(self, collection: str, doc_id: str, data: dict) -> None: ...

    @abstractmethod
    def delete(self, collection: str, doc_id: str) -> None: ...

    @abstractmethod
    def clear(self, collection: str) -> None: ...


class Repository(Generic[ModelT]):
    """Typed CRUD over one collection."""

    def __init__(
        self, store: DocumentStore, collection: str, model: type[ModelT]
    ) -> None:
        self._store = store
        self._collection = collection
        self._model = model

    @property
    def collection(self) -> str:
        return self._collection

    def _parse(self, raw: dict) -> ModelT:
        return self._model.model_validate(raw)

    def _serialise(self, entity: ModelT) -> dict:
        # JSON mode keeps the wire format identical across storage backends:
        # datetimes become ISO-8601 UTC strings that sort lexicographically.
        return entity.model_dump(mode="json")

    def get(self, doc_id: str) -> ModelT | None:
        raw = self._store.get(self._collection, doc_id)
        return self._parse(raw) if raw is not None else None

    def require(self, doc_id: str) -> ModelT:
        entity = self.get(doc_id)
        if entity is None:
            raise EntityNotFound(self._collection, doc_id)
        return entity

    def list_all(self) -> list[ModelT]:
        return [self._parse(raw) for raw in self._store.list(self._collection)]

    def find(self, predicate: Callable[[ModelT], bool]) -> list[ModelT]:
        return [entity for entity in self.list_all() if predicate(entity)]

    def find_one(self, predicate: Callable[[ModelT], bool]) -> ModelT | None:
        for entity in self.list_all():
            if predicate(entity):
                return entity
        return None

    def save(self, entity: ModelT) -> ModelT:
        doc_id = entity.id
        self._store.set(self._collection, doc_id, self._serialise(entity))
        return entity

    def save_many(self, entities: Iterable[ModelT]) -> None:
        for entity in entities:
            self.save(entity)

    def delete(self, doc_id: str) -> None:
        self._store.delete(self._collection, doc_id)

    def clear(self) -> None:
        self._store.clear(self._collection)

    def count(self) -> int:
        return len(self._store.list(self._collection))
