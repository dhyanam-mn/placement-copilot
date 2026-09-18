from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from services.gmail_tracker import sync_gmail_tracker, load_sync_state, get_gmail_service

router = APIRouter(prefix="/tracker/gmail", tags=["Gmail Tracker Agent"])


class MockMessageItem(BaseModel):
    id: Optional[str] = None
    history_id: Optional[str] = None
    sender: str
    subject: str
    body: str


class SyncRequest(BaseModel):
    mock_messages: Optional[List[MockMessageItem]] = None


@router.post("/sync")
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


@router.get("/status")
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
