"""The :class:`Database` facade: one typed repository per collection."""

from __future__ import annotations

from app.core.config import Settings
from app.repositories.base import DocumentStore, Repository
from app.repositories.memory import InMemoryDocumentStore
from app.schemas.domain import (
    ActionItem,
    AISummaryCache,
    AuditEvent,
    DecisionRecord,
    HandoverRecord,
    Milestone,
    Notification,
    Project,
    ProjectDocument,
    SupportRequest,
    Task,
    TaskUpdate,
    User,
)

COLLECTIONS = (
    "users",
    "projects",
    "milestones",
    "tasks",
    "task_updates",
    "documents",
    "decisions",
    "support_requests",
    "action_items",
    "handovers",
    "notifications",
    "audit_events",
    "ai_cache",
)


class Database:
    """Aggregates every repository behind one object passed through the app."""

    def __init__(self, store: DocumentStore) -> None:
        self.store = store
        self.users: Repository[User] = Repository(store, "users", User)
        self.projects: Repository[Project] = Repository(store, "projects", Project)
        self.milestones: Repository[Milestone] = Repository(
            store, "milestones", Milestone
        )
        self.tasks: Repository[Task] = Repository(store, "tasks", Task)
        self.task_updates: Repository[TaskUpdate] = Repository(
            store, "task_updates", TaskUpdate
        )
        self.documents: Repository[ProjectDocument] = Repository(
            store, "documents", ProjectDocument
        )
        self.decisions: Repository[DecisionRecord] = Repository(
            store, "decisions", DecisionRecord
        )
        self.requests: Repository[SupportRequest] = Repository(
            store, "support_requests", SupportRequest
        )
        self.actions: Repository[ActionItem] = Repository(
            store, "action_items", ActionItem
        )
        self.handovers: Repository[HandoverRecord] = Repository(
            store, "handovers", HandoverRecord
        )
        self.notifications: Repository[Notification] = Repository(
            store, "notifications", Notification
        )
        self.audit: Repository[AuditEvent] = Repository(
            store, "audit_events", AuditEvent
        )
        self.ai_cache: Repository[AISummaryCache] = Repository(
            store, "ai_cache", AISummaryCache
        )

    def clear_all(self) -> None:
        """Wipe every known collection. Guarded by the seed endpoint's config."""
        for collection in COLLECTIONS:
            self.store.clear(collection)

    def is_empty(self) -> bool:
        return self.users.count() == 0


def build_store(settings: Settings) -> DocumentStore:
    if settings.data_backend == "firestore":
        from app.repositories.firestore import FirestoreDocumentStore

        return FirestoreDocumentStore(
            project_id=settings.firestore_project_id,
            database=settings.firestore_database,
            collection_prefix=settings.firestore_collection_prefix,
        )
    return InMemoryDocumentStore()


def build_database(settings: Settings) -> Database:
    return Database(build_store(settings))
