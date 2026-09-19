from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import Notification
from schemas import NotificationResponse, NotificationListResponse

router = APIRouter(tags=["Notifications"])


@router.get("/notifications", response_model=NotificationListResponse)
def get_notifications(
    unread_only: bool = False,
    unread: Optional[bool] = None,
    db: Session = Depends(get_db),
):
    """List system notifications, optionally filtering for unread notifications."""
    query = db.query(Notification)
    if unread_only or (unread is True):
        query = query.filter(Notification.read == False)
    elif unread is False:
        query = query.filter(Notification.read == True)

    notifications = query.order_by(Notification.created_at.desc()).all()
    return NotificationListResponse(notifications=notifications)


@router.post("/notifications/{id}/read", response_model=NotificationResponse)
def mark_notification_as_read(id: int, db: Session = Depends(get_db)):
    """Mark a notification record as read by ID."""
    notif = db.query(Notification).filter(Notification.id == id).first()
    if not notif:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "detail": f"notification id {id} does not exist"},
        )
    notif.read = True
    db.commit()
    db.refresh(notif)
    return notif
