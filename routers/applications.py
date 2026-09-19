import logging
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session
import numpy as np

logger = logging.getLogger("placement_copilot.applications")

from database import get_db
from models import Application, GapReport, StatusEvent, ScamCheck
from schemas import (
    ApplicationCreateRequest,
    ApplicationListResponse,
    ApplicationResponse,
    ApplicationStatusPatchRequest,
    GapReportResponse,
    PrepResponse,
    PrepRecommendationItem,
    ScamCheckRequest,
    ScamCheckResponse,
    StatusEventListResponse,
    StatusEventResponse,
    TailorResponse,
)
from services.model_service_client import (
    call_embed,
    ModelServiceUnavailableError,
)
from services.tailoring import tailor_resume_for_application, _load_base_resume
from services.gap_agent import (
    generate_per_row_gap_report,
    generate_aggregate_gap_report,
)
from services.scam_check import run_scam_check

router = APIRouter(tags=["Applications"])


def _cosine_similarity(v1: list, v2: list) -> float:
    """Compute cosine similarity between two float vectors."""
    a = np.array(v1, dtype=float)
    b = np.array(v2, dtype=float)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


# --- 1. GET /applications ---
@router.get("/applications", response_model=ApplicationListResponse)
def get_applications(
    status: Optional[str] = Query(None, description="Filter by application status"),
    source: Optional[str] = Query(None, description="Filter by job source"),
    is_demo: Optional[bool] = Query(None, description="Filter by demo flag"),
    db: Session = Depends(get_db),
):
    query = db.query(Application)
    if status:
        valid_statuses = {
            "DISCOVERED", "READY_TO_APPLY", "APPLIED",
            "OA_INVITE", "INTERVIEW", "REJECTED", "GHOSTED", "OFFER"
        }
        if status not in valid_statuses:
            raise HTTPException(
                status_code=422,
                detail={"error": "validation_error", "detail": f"Invalid status '{status}'"},
            )
        query = query.filter(Application.status == status)
    if source:
        query = query.filter(Application.source == source)
    if is_demo is not None:
        query = query.filter(Application.is_demo == is_demo)

    apps = query.order_by(Application.id.asc()).all()
    return ApplicationListResponse(applications=apps)


# --- 2. GET /applications/{id} ---
@router.get("/applications/{id}", response_model=ApplicationResponse)
def get_application_by_id(id: int, db: Session = Depends(get_db)):
    app = db.query(Application).filter(Application.id == id).first()
    if not app:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "detail": f"application id {id} does not exist"},
        )
    return app


# --- 2b. GET /applications/{id}/events ---
@router.get("/applications/{id}/events", response_model=StatusEventListResponse)
def get_application_events(id: int, db: Session = Depends(get_db)):
    """Retrieve history of status transition events for a given application ID."""
    app = db.query(Application).filter(Application.id == id).first()
    if not app:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "detail": f"application id {id} does not exist"},
        )
    events = (
        db.query(StatusEvent)
        .filter(StatusEvent.application_id == id)
        .order_by(StatusEvent.created_at.asc())
        .all()
    )
    return StatusEventListResponse(events=events)


async def process_and_create_application(
    payload: ApplicationCreateRequest, db: Session
) -> Application:
    """Core logic to embed JD against base resume bullets, calculate match score, and store application."""
    # Check if application already exists in DB (ON CONFLICT DO NOTHING semantics)
    existing = (
        db.query(Application)
        .filter(
            func.lower(Application.company) == payload.company.lower().strip(),
            func.lower(Application.role) == payload.role.lower().strip(),
            Application.source == payload.source,
        )
        .first()
    )
    if existing:
        return existing

    base_bullets = _load_base_resume(db)
    sample_bullets = [b["bullet"] for b in base_bullets]

    texts_to_embed = [payload.jd_text] + sample_bullets

    try:
        embed_data = await call_embed(texts_to_embed)
        embeddings = embed_data.get("embeddings", [])

        if len(embeddings) >= 2:
            jd_emb = embeddings[0]
            bullet_embs = embeddings[1:]
            sim_scores = [_cosine_similarity(jd_emb, b_emb) for b_emb in bullet_embs]
            match_score = round(float(max(sim_scores)), 2)
        else:
            match_score = 0.50
    except (ModelServiceUnavailableError, Exception):
        match_score = 0.50

    new_app = Application(
        company=payload.company,
        role=payload.role,
        jd_text=payload.jd_text,
        source=payload.source,
        status="DISCOVERED",
        status_source=None,
        match_score=match_score,
    )
    db.add(new_app)
    db.commit()
    db.refresh(new_app)

    # Launch LangGraph orchestrator workflow for new application
    from services.orchestrator import run_application_workflow
    try:
        await run_application_workflow(db, new_app)
        db.refresh(new_app)
    except Exception as exc:
        logger.warning(f"Orchestrator initial workflow encountered error for App ID {new_app.id}: {exc}")

    return new_app


# --- 3. POST /applications ---
@router.post("/applications", response_model=ApplicationResponse, status_code=201)
async def create_application(payload: ApplicationCreateRequest, db: Session = Depends(get_db)):
    return await process_and_create_application(payload, db)


# --- 3b. POST /applications/{id}/confirm-applied ---
@router.post("/applications/{id}/confirm-applied", response_model=ApplicationResponse)
async def confirm_application_submission(id: int, db: Session = Depends(get_db)):
    """
    Student/User confirms submission of job application.
    Transitions status to APPLIED and resumes LangGraph orchestrator past READY_TO_APPLY checkpoint.
    """
    app = db.query(Application).filter(Application.id == id).first()
    if not app:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "detail": f"application id {id} does not exist"},
        )

    from services.orchestrator import confirm_application_applied
    await confirm_application_applied(db, app.id)
    db.refresh(app)
    return app


# --- 3c. POST /scout/sync ---
@router.post("/scout/sync")
async def trigger_scout_job_sourcing(
    dry_run: bool = Query(False, description="Set true to preview jobs without saving to DB"),
    db: Session = Depends(get_db),
):
    """Trigger Scout Agent live job sourcing from Adzuna, Greenhouse, Lever, and Unstop."""
    from services.job_sourcing import run_job_sourcing
    result = await run_job_sourcing(db, dry_run=dry_run)
    return result


# --- 4. PATCH /applications/{id}/status ---
@router.patch("/applications/{id}/status", response_model=ApplicationResponse)
async def update_application_status(
    id: int, payload: ApplicationStatusPatchRequest, db: Session = Depends(get_db)
):
    from services.status_service import set_status
    try:
        updated_app = await set_status(
            db,
            application_id=id,
            new_status=payload.status,
            source=payload.status_source or "manual"
        )
        return updated_app
    except ValueError as err:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "detail": str(err)},
        )


# --- 5. POST /applications/{id}/tailor ---
@router.post("/applications/{id}/tailor", response_model=TailorResponse)
def tailor_application(id: int, db: Session = Depends(get_db)):
    app = db.query(Application).filter(Application.id == id).first()
    if not app:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "detail": f"application id {id} does not exist"},
        )

    result = tailor_resume_for_application(db, app)
    return result


# --- 6. GET /applications/{id}/gap-report ---
@router.get("/applications/{id}/gap-report", response_model=GapReportResponse)
def get_application_gap_report(id: int, db: Session = Depends(get_db)):
    app = db.query(Application).filter(Application.id == id).first()
    if not app:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "detail": f"application id {id} does not exist"},
        )

    gap_report = (
        db.query(GapReport)
        .filter(GapReport.application_id == id, GapReport.report_type == "per_row")
        .first()
    )
    if not gap_report:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "detail": f"gap report for application id {id} does not exist"},
        )

    return gap_report


# --- 7. POST /applications/{id}/gap-report ---
@router.post("/applications/{id}/gap-report", response_model=GapReportResponse)
async def generate_application_gap_report(id: int, db: Session = Depends(get_db)):
    app = db.query(Application).filter(Application.id == id).first()
    if not app:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "detail": f"application id {id} does not exist"},
        )

    gap_report = await generate_per_row_gap_report(db, app)
    return gap_report


# --- 8. GET /gap-report ---
@router.get("/gap-report", response_model=GapReportResponse)
async def get_aggregate_gap_report(db: Session = Depends(get_db)):
    gap_report = await generate_aggregate_gap_report(db)
    return gap_report


# --- 9. GET /applications/{id}/scam-check ---
@router.get("/applications/{id}/scam-check", response_model=ScamCheckResponse)
def get_application_stored_scam_check(id: int, db: Session = Depends(get_db)):
    """Retrieve latest stored scam-check evaluation & evidence for a given application ID."""
    app = db.query(Application).filter(Application.id == id).first()
    if not app:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "detail": f"application id {id} does not exist"},
        )

    scam_record = (
        db.query(ScamCheck)
        .filter(ScamCheck.application_id == id)
        .order_by(ScamCheck.created_at.desc())
        .first()
    )
    if not scam_record:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "detail": f"scam check record for application id {id} does not exist"},
        )

    return scam_record


# --- 9b. POST /applications/{id}/scam-check ---
@router.post("/applications/{id}/scam-check", response_model=ScamCheckResponse)
async def run_application_scam_check(
    id: int, payload: ScamCheckRequest, db: Session = Depends(get_db)
):
    app = db.query(Application).filter(Application.id == id).first()
    if not app:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "detail": f"application id {id} does not exist"},
        )

    scam_record = await run_scam_check(
        db, app, payload.recruiter_name, payload.recruiter_domain, payload.claimed_company
    )
    return scam_record


# --- 10. GET /applications/{id}/prep ---
@router.get("/applications/{id}/prep")
def get_application_prep(id: int, db: Session = Depends(get_db)):
    app = db.query(Application).filter(Application.id == id).first()
    if not app:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "detail": f"application id {id} does not exist"},
        )
    from services.prep_agent import get_application_prep_recommendations
    recs = get_application_prep_recommendations(db, id)
    return {"application_id": id, "recommendations": recs}


# --- 10b. POST /applications/{id}/prep ---
@router.post("/applications/{id}/prep")
async def generate_application_prep(id: int, db: Session = Depends(get_db)):
    app = db.query(Application).filter(Application.id == id).first()
    if not app:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "detail": f"application id {id} does not exist"},
        )
    from services.prep_agent import generate_prep_recommendations
    recs = await generate_prep_recommendations(db, app)
    return {"application_id": id, "recommendations": recs}
