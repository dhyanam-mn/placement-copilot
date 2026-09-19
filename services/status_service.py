import logging
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session
from models import Application, StatusEvent, Notification

logger = logging.getLogger("placement_copilot.status_service")

async def set_status(
    db: Session,
    application_id: int,
    new_status: str,
    source: Optional[str] = None
) -> Application:
    """
    Unified status transition function for API, Gmail tracker, auto-ghost, scheduler, and LangGraph orchestrator.
    - Updates application status & status_source
    - Updates last_updated timestamp
    - Updates last_contact_date ONLY IF source != 'auto_ghost'
    - Writes status_events entry (old, new, source, timestamp)
    - Triggers Prep Agent on INTERVIEW
    - Triggers per-row Gap report & notification on GHOSTED / REJECTED
    """
    app = db.query(Application).filter(Application.id == application_id).first()
    if not app:
        raise ValueError(f"Application id {application_id} not found.")

    old_status = app.status
    if old_status != new_status or app.status_source != source:
        app.status = new_status
        app.status_source = source
        app.last_updated = datetime.now(timezone.utc)

        if source != "auto_ghost":
            app.last_contact_date = datetime.now(timezone.utc)

        # Write status_events entry
        event = StatusEvent(
            application_id=app.id,
            old_status=old_status,
            new_status=new_status,
            event_source=source,
            is_demo=app.is_demo
        )
        db.add(event)
        db.commit()
        db.refresh(app)

        # Trigger Prep recommendations on INTERVIEW
        if new_status == "INTERVIEW":
            try:
                from services.prep_agent import generate_prep_recommendations
                await generate_prep_recommendations(db, app)
            except Exception as e:
                logger.error(f"Error triggering prep recommendations for app {app.id}: {e}")

        # Trigger per-row Gap report & Notification on GHOSTED / REJECTED
        elif new_status in ("GHOSTED", "REJECTED"):
            try:
                from services.gap_agent import generate_per_row_gap_report
                gap_rep = await generate_per_row_gap_report(db, app)
                if gap_rep:
                    app.gap_report_id = gap_rep.id
                    db.commit()
            except Exception as e:
                logger.error(f"Error generating per-row gap report for app {app.id}: {e}")

            try:
                notif_content = f"Application for '{app.role}' at '{app.company}' transitioned to {new_status}."
                notif = Notification(
                    type=f"STATUS_{new_status}",
                    content=notif_content,
                    read=False,
                    is_demo=app.is_demo
                )
                db.add(notif)
                db.commit()
            except Exception as e:
                logger.error(f"Error creating notification for app {app.id}: {e}")

    return app
