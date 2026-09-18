from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
import numpy as np

from database import get_db
from models import Application, GapReport
from schemas import (
    ApplicationCreateRequest,
    ApplicationListResponse,
    ApplicationResponse,
    ApplicationStatusPatchRequest,
    GapReportResponse,
    PrepEvaluateRequest,
    PrepEvaluateResponse,
    ScamCheckRequest,
    ScamCheckResponse,
    TailorResponse,
)
from services.model_service_client import (
    call_embed,
    call_prep_evaluate_answer,
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


# --- 3. POST /applications ---
@router.post("/applications", response_model=ApplicationResponse, status_code=201)
async def create_application(payload: ApplicationCreateRequest, db: Session = Depends(get_db)):
    base_bullets = _load_base_resume()
    sample_bullets = [b["bullet"] for b in base_bullets]

    texts_to_embed = [payload.jd_text] + sample_bullets

    # Calls model-service /embed at localhost:8001
    embed_data = await call_embed(texts_to_embed)
    embeddings = embed_data.get("embeddings", [])

    if len(embeddings) >= 2:
        jd_emb = embeddings[0]
        bullet_embs = embeddings[1:]
        sim_scores = [_cosine_similarity(jd_emb, b_emb) for b_emb in bullet_embs]
        match_score = round(float(max(sim_scores)), 2)
    else:
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

    return new_app


# --- 4. PATCH /applications/{id}/status ---
@router.patch("/applications/{id}/status", response_model=ApplicationResponse)
async def update_application_status(
    id: int, payload: ApplicationStatusPatchRequest, db: Session = Depends(get_db)
):
    app = db.query(Application).filter(Application.id == id).first()
    if not app:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "detail": f"application id {id} does not exist"},
        )

    app.status = payload.status
    if payload.status_source:
        app.status_source = payload.status_source

    db.commit()
    db.refresh(app)

    # Automatic Gap Report Trigger if status becomes GHOSTED or REJECTED
    if payload.status in ("GHOSTED", "REJECTED"):
        await generate_per_row_gap_report(db, app)
        db.refresh(app)

    return app


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


# --- 9. POST /applications/{id}/scam-check ---
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


# --- 10. POST /applications/{id}/prep/evaluate-answer ---
@router.post("/applications/{id}/prep/evaluate-answer", response_model=PrepEvaluateResponse)
async def evaluate_prep_answer(
    id: int, payload: PrepEvaluateRequest, db: Session = Depends(get_db)
):
    app = db.query(Application).filter(Application.id == id).first()
    if not app:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "detail": f"application id {id} does not exist"},
        )

    # Pass straight through to model-service /prep/evaluate-answer
    result = await call_prep_evaluate_answer(
        payload.question, payload.student_answer, payload.question_tags
    )
    return result
