"""Cloud Firestore document store.

Imported lazily so that local development and the test suite never require
google-cloud credentials.
"""

from __future__ import annotations

from app.repositories.base import DocumentStore


class FirestoreDocumentStore(DocumentStore):
    def __init__(
        self,
        project_id: str | None = None,
        database: str = "(default)",
        collection_prefix: str = "",
    ) -> None:
        from google.cloud import firestore  # imported here on purpose

        kwargs: dict[str, object] = {}
        if project_id:
            kwargs["project"] = project_id
        if database and database != "(default)":
            kwargs["database"] = database
        self._client = firestore.Client(**kwargs)
        self._prefix = collection_prefix

    def _name(self, collection: str) -> str:
        return f"{self._prefix}{collection}"

    def get(self, collection: str, doc_id: str) -> dict | None:
        snapshot = self._client.collection(self._name(collection)).document(doc_id).get()
        return snapshot.to_dict() if snapshot.exists else None

    def list(self, collection: str) -> list[dict]:
        return [
            snapshot.to_dict()
            for snapshot in self._client.collection(self._name(collection)).stream()
        ]

    def set(self, collection: str, doc_id: str, data: dict) -> None:
        self._client.collection(self._name(collection)).document(doc_id).set(data)

    def delete(self, collection: str, doc_id: str) -> None:
        self._client.collection(self._name(collection)).document(doc_id).delete()

    def clear(self, collection: str) -> None:
        """Delete every document in a collection, in batches.

        Only reachable through the seed-reset path, which is disabled outside
        local/staging.
        """
        ref = self._client.collection(self._name(collection))
        while True:
            documents = list(ref.limit(400).stream())
            if not documents:
                return
            batch = self._client.batch()
            for document in documents:
                batch.delete(document.reference)
            batch.commit()
