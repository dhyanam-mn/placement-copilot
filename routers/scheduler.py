from typing import Dict, List, Any
from fastapi import APIRouter, HTTPException, status
from services.scheduler import get_scheduled_jobs_status, trigger_job_by_id

router = APIRouter(prefix="/admin/scheduler", tags=["Scheduler Admin"])


@router.get("/jobs", response_model=List[Dict[str, Any]])
def list_scheduled_jobs():
    """Lists all active APScheduler background jobs, their schedules, and next run times."""
    return get_scheduled_jobs_status()


@router.post("/{job_id}/trigger")
async def trigger_scheduled_job(job_id: str):
    """
    Manually triggers a background job immediately.
    Supported job_ids: 'scout_sync', 'gmail_sync_auto_ghost', 'gap_aggregate'.
    """
    try:
        res = await trigger_job_by_id(job_id)
        return res
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "job_not_found", "detail": str(val_err)},
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "job_trigger_failed", "detail": str(exc)},
        )
