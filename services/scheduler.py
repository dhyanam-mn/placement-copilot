import os
import logging
from typing import Dict, List, Any
from datetime import datetime, timezone
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from database import SessionLocal
from services.job_sourcing import run_job_sourcing
from services.gmail_tracker import sync_gmail_tracker, run_auto_ghost_sweep
from services.gap_agent import generate_aggregate_gap_report

logger = logging.getLogger("placement_copilot.scheduler")

SCOUT_SYNC_INTERVAL_HOURS = int(os.getenv("SCOUT_SYNC_INTERVAL_HOURS", "6"))
GMAIL_SYNC_INTERVAL_HOURS = int(os.getenv("GMAIL_SYNC_INTERVAL_HOURS", "24"))
GAP_AGGREGATE_INTERVAL_DAYS = int(os.getenv("GAP_AGGREGATE_INTERVAL_DAYS", "7"))

scheduler = AsyncIOScheduler()


# ==============================================================================
# SCHEDULED JOB WRAPPERS
# ==============================================================================

async def scheduled_scout_job():
    """APScheduler Job: Runs Scout Agent live job sourcing."""
    logger.info("[Scheduler] Starting scheduled Scout job sourcing...")
    db = SessionLocal()
    try:
        res = await run_job_sourcing(db, dry_run=False)
        logger.info(f"[Scheduler] Scout job sourcing complete. Inserted {res.get('total_inserted', 0)} jobs.")
    except Exception as exc:
        logger.error(f"[Scheduler] Scout job sourcing failed: {exc}", exc_info=True)
    finally:
        db.close()


async def scheduled_gmail_auto_ghost_job():
    """APScheduler Job: Runs Gmail email tracker & 45-day auto-ghost sweep."""
    logger.info("[Scheduler] Starting scheduled Gmail tracker & auto-ghost sweep...")
    db = SessionLocal()
    try:
        gmail_res = await sync_gmail_tracker(db)
        ghost_res = await run_auto_ghost_sweep(db)
        logger.info(f"[Scheduler] Gmail sync matched {len(gmail_res.get('updated_applications', []))} emails. Auto-ghosted {ghost_res.get('total_ghosted', 0)} applications.")
    except Exception as exc:
        logger.error(f"[Scheduler] Gmail tracker / auto-ghost sweep failed: {exc}", exc_info=True)
    finally:
        db.close()


async def scheduled_gap_aggregate_job():
    """APScheduler Job: Runs aggregate gap analysis report."""
    logger.info("[Scheduler] Starting scheduled aggregate gap report generation...")
    db = SessionLocal()
    try:
        res = await generate_aggregate_gap_report(db)
        logger.info(f"[Scheduler] Aggregate gap analysis complete.")
    except Exception as exc:
        logger.error(f"[Scheduler] Aggregate gap analysis failed: {exc}", exc_info=True)
    finally:
        db.close()


# ==============================================================================
# SCHEDULER LIFECYCLE MANAGEMENT
# ==============================================================================

def start_scheduler():
    """Initializes and starts the APScheduler background scheduler."""
    if not scheduler.running:
        db = SessionLocal()
        try:
            from services.settings_service import get_scout_interval_hours
            scout_interval = get_scout_interval_hours(db)
        except Exception:
            scout_interval = SCOUT_SYNC_INTERVAL_HOURS
        finally:
            db.close()

        scheduler.add_job(
            scheduled_scout_job,
            trigger=IntervalTrigger(hours=scout_interval),
            id="scout_sync",
            name="Scout Live Job Sourcing",
            replace_existing=True,
        )
        scheduler.add_job(
            scheduled_gmail_auto_ghost_job,
            trigger=IntervalTrigger(hours=GMAIL_SYNC_INTERVAL_HOURS),
            id="gmail_sync_auto_ghost",
            name="Gmail Sync & Auto-Ghosting",
            replace_existing=True,
        )
        scheduler.add_job(
            scheduled_gap_aggregate_job,
            trigger=IntervalTrigger(days=GAP_AGGREGATE_INTERVAL_DAYS),
            id="gap_aggregate",
            name="Weekly Aggregate Gap Analysis",
            replace_existing=True,
        )
        scheduler.start()
        logger.info("[Scheduler] APScheduler started successfully.")


def shutdown_scheduler():
    """Shuts down the APScheduler background scheduler safely."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("[Scheduler] APScheduler shut down.")


def get_scheduled_jobs_status() -> List[Dict[str, Any]]:
    """Returns status and next run times for all scheduled jobs."""
    jobs_info = []
    for job in scheduler.get_jobs():
        jobs_info.append({
            "id": job.id,
            "name": job.name,
            "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
            "trigger": str(job.trigger),
        })
    return jobs_info


async def trigger_job_by_id(job_id: str) -> Dict[str, Any]:
    """Manually triggers a scheduled job immediately by ID."""
    if job_id == "scout_sync":
        await scheduled_scout_job()
        return {"status": "triggered", "job_id": job_id, "message": "Scout job sourcing executed."}
    elif job_id == "gmail_sync_auto_ghost":
        await scheduled_gmail_auto_ghost_job()
        return {"status": "triggered", "job_id": job_id, "message": "Gmail sync & auto-ghosting executed."}
    elif job_id == "gap_aggregate":
        await scheduled_gap_aggregate_job()
        return {"status": "triggered", "job_id": job_id, "message": "Aggregate gap analysis executed."}
    else:
        raise ValueError(f"Unknown job_id '{job_id}'. Valid IDs: scout_sync, gmail_sync_auto_ghost, gap_aggregate.")
