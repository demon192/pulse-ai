"""Intelligent handover workflow.

Sequence: request -> deterministic impact analysis -> candidate ranking ->
AI brief -> manager approval -> backup acceptance -> task reassignment.

Task ownership only changes at the very last step, and only after a manager has
approved *and* the selected backup has accepted. Eligibility gates are
re-evaluated at approval time, not just when candidates were ranked.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from app.ai.schemas import HANDOVER_SECTION_HEADINGS
from app.ai.service import AIService
from app.core.clock import utc_now
from app.core.logging import get_logger
from app.models.enums import (
    ActionStatus,
    ActionType,
    ApprovalStatus,
    AvailabilityStatus,
    HandoverStatus,
    NotificationType,
    Priority,
    Role,
)
from app.notifications.service import NotificationService, make_dedup_key
from app.repositories.database import Database
from app.rules.candidates import (
    check_eligibility,
    explain_no_candidate,
    rank_candidates,
)
from app.rules.dependencies import DependencyGraph
from app.schemas.analysis import Evidence, HandoverAnalysis
from app.schemas.domain import (
    HandoverBrief,
    HandoverBriefSection,
    HandoverRecord,
    Task,
    User,
)
from app.services import actions as action_service
from app.services import audit, authz
from app.services import facts as facts_builder

logger = get_logger(__name__)

# How many affected tasks get a full AI brief. Keeps a single analyse call
# bounded; the rest are listed in the impact analysis.
MAX_BRIEFED_TASKS = 3


def new_handover_id() -> str:
    return f"hdv-{uuid.uuid4().hex[:12]}"


class HandoverService:
    def __init__(
        self,
        database: Database,
        notifications: NotificationService,
        ai_service: AIService,
    ) -> None:
        self.db = database
        self.notifications = notifications
        self.ai = ai_service

    # -- creation -------------------------------------------------------
    def create(
        self,
        *,
        actor: User,
        unavailable_user_id: str,
        start_time: datetime,
        expected_return: datetime | None = None,
        reason_category: str = "unplanned_leave",
        handover_notes: str | None = None,
        affected_task_ids: list[str] | None = None,
        now: datetime | None = None,
    ) -> HandoverRecord:
        """Record an availability change. No medical or family detail is stored."""
        now = now or utc_now()
        if actor.id != unavailable_user_id and actor.role is not Role.MANAGER:
            raise authz.AuthorizationError(
                "You can only raise a handover for yourself."
            )
        unavailable_user = self.db.users.require(unavailable_user_id)
        if actor.role is Role.MANAGER and actor.id != unavailable_user_id:
            overlap = set(unavailable_user.authorized_project_ids) & authz.accessible_project_ids(
                self.db, actor
            )
            if not overlap:
                raise authz.AuthorizationError(
                    "You do not manage any project this engineer works on."
                )

        handover = HandoverRecord(
            id=new_handover_id(),
            unavailable_user_id=unavailable_user_id,
            requested_by=actor.id,
            reason_category=reason_category,
            start_time=start_time,
            expected_return=expected_return,
            handover_notes=handover_notes,
            affected_task_ids=affected_task_ids or [],
            handover_status=HandoverStatus.DRAFT,
            manager_approval_status=ApprovalStatus.PENDING,
            created_at=now,
            updated_at=now,
            is_demo_data=False,
        )
        self.db.handovers.save(handover)

        # Reflect availability immediately when the absence has already begun.
        if start_time <= now and unavailable_user.availability_status in (
            AvailabilityStatus.AVAILABLE,
            AvailabilityStatus.LIMITED,
        ):
            self.db.users.save(
                unavailable_user.model_copy(
                    update={"availability_status": AvailabilityStatus.UNAVAILABLE}
                )
            )

        audit.record(
            self.db,
            actor_id=actor.id,
            action="handover.create",
            entity_type="handover",
            entity_id=handover.id,
            details={"unavailable_user_id": unavailable_user_id},
        )
        return handover

    # -- analysis -------------------------------------------------------
    def analyze(
        self,
        *,
        handover: HandoverRecord,
        actor: User,
        now: datetime | None = None,
        generate_briefs: bool = True,
    ) -> tuple[HandoverRecord, HandoverAnalysis]:
        """Deterministic impact analysis plus AI briefs for the top tasks."""
        now = now or utc_now()
        if not authz.can_view_handover(self.db, actor, handover):
            raise authz.AuthorizationError("You are not authorized to analyse this handover.")

        unavailable_user = self.db.users.require(handover.unavailable_user_id)
        all_tasks = self.db.tasks.list_all()
        graph = DependencyGraph(all_tasks)

        # 1. Active tasks owned by the unavailable engineer.
        active_tasks = [
            task
            for task in all_tasks
            if task.owner_id == unavailable_user.id and task.is_open
        ]
        if handover.affected_task_ids:
            requested = set(handover.affected_task_ids)
            active_tasks = [task for task in active_tasks if task.id in requested] or active_tasks
        active_tasks.sort(
            key=lambda task: (
                -_priority_rank(task.priority),
                task.due_date or datetime.max.replace(tzinfo=now.tzinfo),
            )
        )

        # 2. Dependency-linked work.
        downstream_ids = graph.downstream_task_ids([task.id for task in active_tasks])

        # Upstream work the active tasks are waiting on. It is not reassigned,
        # but a pending approval on it is exactly what the backup must know.
        upstream_blocking_ids = sorted(
            {
                upstream.id
                for task in active_tasks
                for upstream in graph.upstream(task.id)
                if upstream.is_open
            }
            - {task.id for task in active_tasks}
        )

        # 3. Deadlines and milestones.
        affected_project_ids = sorted({task.project_id for task in active_tasks})
        touched_task_ids = {task.id for task in active_tasks} | set(downstream_ids)
        context_task_ids = touched_task_ids | set(upstream_blocking_ids)
        affected_milestones = [
            milestone
            for milestone in self.db.milestones.list_all()
            if not milestone.completed and touched_task_ids.intersection(milestone.task_ids)
        ]

        # 4. Documentation, decisions, updates and pending approvals.
        pending_actions = self.db.actions.find(
            lambda item: item.is_open
            and (
                item.task_id in context_task_ids
                or item.owner_id == unavailable_user.id
            )
        )
        open_requests = self.db.requests.find(
            lambda item: item.is_open
            and (item.engineer_id == unavailable_user.id or item.task_id in context_task_ids)
        )
        relevant_documents = self.db.documents.find(
            lambda doc: bool(set(doc.task_ids) & context_task_ids)
            or doc.project_id in affected_project_ids
        )

        # 5 & 6. Eligible, ranked backup candidates.
        candidates = rank_candidates(
            self.db.users.list_all(),
            unavailable_user_id=unavailable_user.id,
            tasks=active_tasks,
        )
        no_candidate_note = explain_no_candidate(candidates)

        # 7. AI briefs for the highest-impact tasks.
        briefs: list[HandoverBrief] = []
        missing_information: list[str] = []
        briefed = active_tasks[:MAX_BRIEFED_TASKS] if generate_briefs else []
        for task in briefed:
            brief, task_missing = self._build_brief(
                handover=handover,
                task=task,
                graph=graph,
                unavailable_user=unavailable_user,
                now=now,
            )
            briefs.append(brief)
            missing_information.extend(task_missing)

        if not handover.handover_notes:
            missing_information.append(
                "No handover notes were supplied by the engineer."
            )
        if no_candidate_note:
            missing_information.append(no_candidate_note)
        for task in active_tasks[MAX_BRIEFED_TASKS:]:
            missing_information.append(
                f"'{task.title}' is affected but was not briefed in this pass."
            )

        evidence = self._build_evidence(
            active_tasks=active_tasks,
            downstream_ids=downstream_ids,
            upstream_blocking_ids=upstream_blocking_ids,
            graph=graph,
            milestones=affected_milestones,
            pending_actions=pending_actions,
            now=now,
        )

        updated = handover.model_copy(
            update={
                "affected_task_ids": [task.id for task in active_tasks],
                "affected_project_ids": affected_project_ids,
                "downstream_task_ids": downstream_ids,
                "affected_milestone_ids": [m.id for m in affected_milestones],
                "pending_approval_action_ids": [item.id for item in pending_actions],
                "relevant_document_ids": [doc.id for doc in relevant_documents],
                "candidate_recommendations": candidates,
                "generated_brief": briefs,
                "missing_information": _dedupe(missing_information),
                "handover_status": HandoverStatus.PENDING_MANAGER_REVIEW,
                "updated_at": now,
            }
        )
        self.db.handovers.save(updated)
        self._request_manager_review(handover=updated, actor=actor, now=now)

        analysis = HandoverAnalysis(
            handover_id=updated.id,
            unavailable_user_id=unavailable_user.id,
            unavailable_user_name=unavailable_user.name,
            active_task_ids=updated.affected_task_ids,
            downstream_task_ids=downstream_ids,
            affected_project_ids=affected_project_ids,
            affected_milestone_ids=updated.affected_milestone_ids,
            upstream_blocking_task_ids=upstream_blocking_ids,
            pending_approval_action_ids=updated.pending_approval_action_ids,
            relevant_document_ids=updated.relevant_document_ids,
            open_request_ids=[item.id for item in open_requests],
            candidates=candidates,
            missing_information=updated.missing_information,
            evidence=evidence,
        )
        audit.record(
            self.db,
            actor_id=actor.id,
            action="handover.analyze",
            entity_type="handover",
            entity_id=updated.id,
            details={
                "affected_tasks": str(len(updated.affected_task_ids)),
                "eligible_candidates": str(
                    sum(1 for item in candidates if item.eligible)
                ),
            },
        )
        return updated, analysis

    def _build_brief(
        self,
        *,
        handover: HandoverRecord,
        task: Task,
        graph: DependencyGraph,
        unavailable_user: User,
        now: datetime,
    ) -> tuple[HandoverBrief, list[str]]:
        task_facts, untrusted, missing = facts_builder.handover_task_facts(
            self.db,
            task=task,
            graph=graph,
            unavailable_user=unavailable_user,
            handover_notes=handover.handover_notes,
            now=now,
        )
        result = self.ai.handover_brief(
            handover_id=handover.id,
            task_id=task.id,
            facts=task_facts,
            untrusted=untrusted,
        )
        payload = result.payload
        sections = [
            HandoverBriefSection(
                key=section["key"],
                heading=HANDOVER_SECTION_HEADINGS.get(section["key"], section["key"]),
                content=section["content"],
                evidence_kind=section["evidence_kind"],
                source_ids=section.get("source_ids", []),
            )
            for section in payload.get("sections", [])
        ]
        brief = HandoverBrief(
            task_id=task.id,
            task_title=task.title,
            sections=sections,
            generated_at=now,
            generated_by=result.source,
        )
        return brief, missing + list(payload.get("missing_information", [])) + result.notes

    def _build_evidence(
        self,
        *,
        active_tasks: list[Task],
        downstream_ids: list[str],
        upstream_blocking_ids: list[str],
        graph: DependencyGraph,
        milestones: list,
        pending_actions: list,
        now: datetime,
    ) -> list[Evidence]:
        evidence = [
            Evidence(
                label=task.title,
                detail=(
                    f"Active task, status '{task.status.value}', priority "
                    f"'{task.priority.value}'"
                    + (f", due {task.due_date.date().isoformat()}" if task.due_date else "")
                    + "."
                ),
                entity_type="task",
                entity_id=task.id,
            )
            for task in active_tasks
        ]
        for task_id in downstream_ids[:6]:
            task = graph.get(task_id)
            if task is not None:
                evidence.append(
                    Evidence(
                        label=task.title,
                        detail="Downstream task that depends on the affected work.",
                        entity_type="task",
                        entity_id=task.id,
                    )
                )
        for task_id in upstream_blocking_ids[:4]:
            task = graph.get(task_id)
            if task is not None:
                evidence.append(
                    Evidence(
                        label=task.title,
                        detail=(
                            "Incomplete upstream dependency the affected work is "
                            f"waiting on (status '{task.status.value}')."
                        ),
                        entity_type="task",
                        entity_id=task.id,
                    )
                )
        for milestone in milestones[:4]:
            evidence.append(
                Evidence(
                    label=milestone.name,
                    detail=f"Milestone target {milestone.target_date.date().isoformat()}.",
                    entity_type="milestone",
                    entity_id=milestone.id,
                )
            )
        for action in pending_actions[:5]:
            evidence.append(
                Evidence(
                    label=action.title,
                    detail=f"Pending {action.type.value.replace('_', ' ')}.",
                    entity_type="action_item",
                    entity_id=action.id,
                )
            )
        return evidence

    def _request_manager_review(
        self, *, handover: HandoverRecord, actor: User, now: datetime
    ) -> None:
        managers = self._managers_for(handover)
        engineer_name = self.db.users.require(handover.unavailable_user_id).name
        for manager_id in managers:
            existing = self.db.actions.find_one(
                lambda item, owner=manager_id: item.source_handover_id == handover.id
                and item.owner_id == owner
                and item.is_open
            )
            if existing is not None:
                continue
            action_service.create_action(
                self.db,
                self.notifications,
                action_type=ActionType.HANDOVER_APPROVAL,
                title=f"Approve handover coverage for {engineer_name}",
                description=(
                    f"{len(handover.affected_task_ids)} active task(s) and "
                    f"{len(handover.downstream_task_ids)} downstream task(s) need coverage. "
                    f"{sum(1 for c in handover.candidate_recommendations if c.eligible)} "
                    "eligible backup candidate(s) were ranked."
                ),
                owner_id=manager_id,
                created_by=actor.id,
                project_id=handover.affected_project_ids[0]
                if handover.affected_project_ids
                else None,
                source_handover_id=handover.id,
                priority=Priority.HIGH,
                suggested_action="Review the brief, pick a backup and approve the handover.",
                now=now,
            )

    def _managers_for(self, handover: HandoverRecord) -> list[str]:
        manager_ids: list[str] = []
        for project_id in handover.affected_project_ids:
            project = self.db.projects.get(project_id)
            if project and project.manager_id not in manager_ids:
                manager_ids.append(project.manager_id)
        if not manager_ids:
            engineer = self.db.users.get(handover.unavailable_user_id)
            if engineer and engineer.manager_id:
                manager_ids.append(engineer.manager_id)
        return manager_ids

    # -- approval -------------------------------------------------------
    def approve(
        self,
        *,
        handover: HandoverRecord,
        manager: User,
        selected_backup_id: str,
        notes: str | None = None,
    ) -> HandoverRecord:
        """Approve a handover and nominate a backup.

        Re-runs the hard eligibility gate so a candidate whose authorisation or
        availability changed after ranking cannot slip through.
        """
        if not authz.can_approve_handover(self.db, manager, handover):
            raise authz.AuthorizationError(
                "Only a manager of an affected project can approve this handover."
            )
        if handover.handover_status in (HandoverStatus.CANCELLED, HandoverStatus.COMPLETED):
            raise ValueError("This handover is already closed.")

        candidate = self.db.users.require(selected_backup_id)
        affected_tasks = [
            self.db.tasks.require(task_id) for task_id in handover.affected_task_ids
        ]
        blocking_reasons = check_eligibility(
            candidate,
            unavailable_user_id=handover.unavailable_user_id,
            tasks=affected_tasks,
        )
        if blocking_reasons:
            raise authz.AuthorizationError(
                f"{candidate.name} is not eligible for this assignment: "
                + " ".join(blocking_reasons)
            )

        now = utc_now()
        updated = handover.model_copy(
            update={
                "manager_approval_status": ApprovalStatus.APPROVED,
                "approved_by": manager.id,
                "approved_at": now,
                "selected_backup_id": selected_backup_id,
                "handover_status": HandoverStatus.APPROVED,
                "updated_at": now,
                "rejection_reason": None,
            }
        )
        self.db.handovers.save(updated)
        self._close_review_actions(updated, resolution=notes or "Handover approved.")

        task_titles = ", ".join(task.title for task in affected_tasks[:3]) or "no tasks"
        self.notifications.emit(
            recipient_id=selected_backup_id,
            notification_type=NotificationType.BACKUP_ASSIGNED,
            title="You have been nominated as backup",
            message=(
                f"{manager.name} nominated you to cover {len(affected_tasks)} task(s): "
                f"{task_titles}."
            ),
            reason="A manager approved a handover and selected you as the backup.",
            suggested_action="Open the handover, read the brief and accept or decline.",
            priority=Priority.HIGH,
            related_entity_type="handover",
            related_entity_id=updated.id,
            dedup_key=make_dedup_key(
                event="backup_assigned",
                entity_type="handover",
                entity_id=updated.id,
                recipient_id=selected_backup_id,
            ),
            now=now,
        )
        self.notifications.emit(
            recipient_id=handover.unavailable_user_id,
            notification_type=NotificationType.HANDOVER_APPROVED,
            title="Your handover was approved",
            message=f"{candidate.name} has been nominated to cover your active work.",
            reason="Your manager approved the handover you requested.",
            suggested_action="No action needed.",
            priority=Priority.MEDIUM,
            related_entity_type="handover",
            related_entity_id=updated.id,
            dedup_key=make_dedup_key(
                event="handover_approved",
                entity_type="handover",
                entity_id=updated.id,
                recipient_id=handover.unavailable_user_id,
            ),
            now=now,
        )
        audit.record(
            self.db,
            actor_id=manager.id,
            action="handover.approve",
            entity_type="handover",
            entity_id=updated.id,
            details={"selected_backup_id": selected_backup_id},
        )
        return updated

    def reject(
        self, *, handover: HandoverRecord, manager: User, reason: str
    ) -> HandoverRecord:
        if not authz.can_approve_handover(self.db, manager, handover):
            raise authz.AuthorizationError(
                "Only a manager of an affected project can reject this handover."
            )
        now = utc_now()
        updated = handover.model_copy(
            update={
                "manager_approval_status": ApprovalStatus.REJECTED,
                "handover_status": HandoverStatus.REJECTED,
                "rejection_reason": reason,
                "approved_by": manager.id,
                "approved_at": now,
                "selected_backup_id": None,
                "updated_at": now,
            }
        )
        self.db.handovers.save(updated)
        self._close_review_actions(updated, resolution=f"Rejected: {reason}")
        audit.record(
            self.db,
            actor_id=manager.id,
            action="handover.reject",
            entity_type="handover",
            entity_id=updated.id,
        )
        return updated

    # -- acceptance and finalisation --------------------------------------
    def accept(self, *, handover: HandoverRecord, backup: User) -> HandoverRecord:
        """The nominated backup accepts; only now is ownership transferred."""
        if handover.selected_backup_id != backup.id:
            raise authz.AuthorizationError(
                "Only the nominated backup can accept this handover."
            )
        if handover.manager_approval_status is not ApprovalStatus.APPROVED:
            raise ValueError(
                "A manager must approve this handover before it can be accepted."
            )

        affected_tasks = [
            self.db.tasks.require(task_id) for task_id in handover.affected_task_ids
        ]
        blocking_reasons = check_eligibility(
            backup,
            unavailable_user_id=handover.unavailable_user_id,
            tasks=affected_tasks,
        )
        if blocking_reasons:
            raise authz.AuthorizationError(
                "You are no longer eligible for this assignment: "
                + " ".join(blocking_reasons)
            )

        now = utc_now()
        reassigned: list[str] = []
        for task in affected_tasks:
            self.db.tasks.save(
                task.model_copy(update={"owner_id": backup.id, "updated_at": now})
            )
            reassigned.append(task.id)

        updated = handover.model_copy(
            update={
                "backup_accepted_at": now,
                "handover_status": HandoverStatus.ACCEPTED,
                "updated_at": now,
            }
        )
        self.db.handovers.save(updated)

        for manager_id in self._managers_for(updated):
            self.notifications.emit(
                recipient_id=manager_id,
                notification_type=NotificationType.HANDOVER_ASSIGNMENT_ACCEPTED,
                title=f"{backup.name} accepted the handover",
                message=f"{len(reassigned)} task(s) were reassigned to {backup.name}.",
                reason="The nominated backup accepted the assignment.",
                suggested_action="No action needed. Coverage is in place.",
                priority=Priority.MEDIUM,
                related_entity_type="handover",
                related_entity_id=updated.id,
                dedup_key=make_dedup_key(
                    event="handover_accepted",
                    entity_type="handover",
                    entity_id=updated.id,
                    recipient_id=manager_id,
                ),
                now=now,
            )
        audit.record(
            self.db,
            actor_id=backup.id,
            action="handover.accept",
            entity_type="handover",
            entity_id=updated.id,
            details={"reassigned_task_count": str(len(reassigned))},
        )
        return updated

    def decline(
        self, *, handover: HandoverRecord, backup: User, reason: str
    ) -> HandoverRecord:
        if handover.selected_backup_id != backup.id:
            raise authz.AuthorizationError(
                "Only the nominated backup can decline this handover."
            )
        now = utc_now()
        updated = handover.model_copy(
            update={
                "handover_status": HandoverStatus.DECLINED,
                "selected_backup_id": None,
                "manager_approval_status": ApprovalStatus.PENDING,
                "rejection_reason": reason,
                "updated_at": now,
            }
        )
        self.db.handovers.save(updated)
        self._request_manager_review(handover=updated, actor=backup, now=now)
        audit.record(
            self.db,
            actor_id=backup.id,
            action="handover.decline",
            entity_type="handover",
            entity_id=updated.id,
        )
        return updated

    def _close_review_actions(self, handover: HandoverRecord, *, resolution: str) -> None:
        for action in self.db.actions.find(
            lambda item: item.source_handover_id == handover.id and item.is_open
        ):
            self.db.actions.save(
                action.model_copy(
                    update={
                        "status": ActionStatus.RESOLVED,
                        "resolution_notes": resolution,
                        "updated_at": utc_now(),
                    }
                )
            )
            self.notifications.resolve_by_entity("action_item", action.id)


def _priority_rank(priority: Priority) -> int:
    return {Priority.LOW: 1, Priority.MEDIUM: 2, Priority.HIGH: 3, Priority.CRITICAL: 4}[
        priority
    ]


def _dedupe(items: list[str]) -> list[str]:
    seen: dict[str, None] = {}
    for item in items:
        if item:
            seen[item] = None
    return list(seen)
