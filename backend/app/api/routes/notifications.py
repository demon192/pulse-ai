"""In-app notifications."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import CurrentUser, Notifications
from app.schemas.api import NotificationList

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=NotificationList)
def list_notifications(
    user: CurrentUser,
    notifications: Notifications,
    unread_only: bool = Query(default=False),
    include_resolved: bool = Query(default=False),
) -> NotificationList:
    items = notifications.for_recipient(
        user.id, include_read=not unread_only, include_resolved=include_resolved
    )
    return NotificationList(
        notifications=items, unread_count=notifications.unread_count(user.id)
    )


@router.post("/{notification_id}/read", response_model=NotificationList)
def mark_read(
    notification_id: str, user: CurrentUser, notifications: Notifications
) -> NotificationList:
    """Marking a notification read never changes the underlying record."""
    updated = notifications.mark_read(notification_id, recipient_id=user.id)
    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found."
        )
    return list_notifications(user, notifications)


@router.post("/{notification_id}/resolve", response_model=NotificationList)
def mark_resolved(
    notification_id: str, user: CurrentUser, notifications: Notifications
) -> NotificationList:
    updated = notifications.mark_resolved(notification_id, recipient_id=user.id)
    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found."
        )
    return list_notifications(user, notifications)
