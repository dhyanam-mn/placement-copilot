from typing import Any, Dict, List, Optional
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models import Application
from services.gmail_tracker import (
    sync_gmail_tracker,
    load_sync_state,
    get_gmail_service,
    get_stale_application_nudges,
    run_auto_ghost_sweep,
)

router = APIRouter(tags=["Tracker Agent"])


class MockMessageItem(BaseModel):
    id: Optional[str] = None
    history_id: Optional[str] = None
    sender: str
    subject: str
    body: str


class SyncRequest(BaseModel):
    mock_messages: Optional[List[MockMessageItem]] = None


class BackdateRequest(BaseModel):
    application_id: Optional[int] = None
    days: int = 46


@router.post("/tracker/gmail/sync")
async def trigger_gmail_sync(
    payload: Optional[SyncRequest] = None,
    db: Session = Depends(get_db),
):
    """
    Triggers a sync of incoming Gmail messages.
    Optionally accepts a list of mock messages in the request body for testing/fixtures.
    Updates application status with status_source='gmail_auto' and triggers gap reports on rejection.
    """
    mock_msgs = None
    if payload and payload.mock_messages is not None:
        mock_msgs = [msg.model_dump() for msg in payload.mock_messages]

    result = await sync_gmail_tracker(db, mock_messages=mock_msgs)
    return result


@router.get("/tracker/gmail/status")
def get_gmail_tracker_status():
    """
    Returns the current Gmail Tracker sync state (last_synced_history_id, last_synced_timestamp, etc.)
    and OAuth connection readiness.
    """
    state = load_sync_state()
    service = get_gmail_service()
    is_authenticated = service is not None

    return {
        "is_authenticated": is_authenticated,
        "sync_state": state,
    }


@router.get("/tracker/nudges")
def get_tracker_nudges(
    days: int = Query(14, ge=1, le=44, description="Staleness threshold in days (below 45 days)"),
    db: Session = Depends(get_db),
):
    """
    Returns open applications stale past threshold days (default 14, up to 44 days).
    """
    return get_stale_application_nudges(db, threshold_days=days)


@router.post("/tracker/auto-ghost")
async def trigger_auto_ghost(db: Session = Depends(get_db)):
    """
    Triggers 45-day auto-ghost staleness sweep.
    Sets status='GHOSTED' and status_source='auto_ghost', preserving last_contact_date.
    """
    return await run_auto_ghost_sweep(db)


@router.post("/tracker/demo/backdate")
@router.post("/admin/demo/backdate")
def demo_backdate_application(
    payload: BackdateRequest,
    db: Session = Depends(get_db),
):
    """
    Demo utility endpoint to backdate application last_contact_date by specified days.
    Enables instant testing of nudges (e.g. 15 days) or auto-ghosting (e.g. 46 days).
    """
    now = datetime.now(timezone.utc)
    target_date = now - timedelta(days=payload.days)

    if payload.application_id:
        app = db.query(Application).filter(Application.id == payload.application_id).first()
        if not app:
            raise HTTPException(
                status_code=404,
                detail={"error": "not_found", "detail": f"application id {payload.application_id} does not exist"},
            )
        app.last_contact_date = target_date
        db.commit()
        db.refresh(app)
        return {
            "status": "success",
            "message": f"Backdated application ID {app.id} by {payload.days} days",
            "application_id": app.id,
            "company": app.company,
            "role": app.role,
            "last_contact_date": app.last_contact_date.isoformat(),
        }
    else:
        open_statuses = ("DISCOVERED", "READY_TO_APPLY", "APPLIED", "OA_INVITE", "INTERVIEW")
        apps = db.query(Application).filter(Application.status.in_(open_statuses)).all()
        for app in apps:
            app.last_contact_date = target_date
        db.commit()
        return {
            "status": "success",
            "message": f"Backdated {len(apps)} open applications by {payload.days} days",
            "total_backdated": len(apps),
            "target_last_contact_date": target_date.isoformat(),
        }
