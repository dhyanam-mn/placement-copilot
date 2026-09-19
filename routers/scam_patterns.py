from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from models import ScamPattern
from schemas import ScamPatternCreateRequest, ScamPatternResponse

router = APIRouter(tags=["Scam Patterns"])


@router.get("/scam-patterns", response_model=List[ScamPatternResponse])
def list_scam_patterns(db: Session = Depends(get_db)):
    """List all registered scam phrase patterns."""
    return db.query(ScamPattern).order_by(ScamPattern.id.asc()).all()


@router.get("/scam-patterns/{id}", response_model=ScamPatternResponse)
def get_scam_pattern_by_id(id: int, db: Session = Depends(get_db)):
    """Get scam pattern details by ID."""
    pattern = db.query(ScamPattern).filter(ScamPattern.id == id).first()
    if not pattern:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "detail": f"scam pattern id {id} does not exist"},
        )
    return pattern


@router.post("/scam-patterns", response_model=ScamPatternResponse, status_code=201)
def create_scam_pattern(payload: ScamPatternCreateRequest, db: Session = Depends(get_db)):
    """Create a new scam detection phrase pattern."""
    pattern = ScamPattern(
        category=payload.category,
        pattern=payload.pattern,
        weight=payload.weight,
        source_note=payload.source_note,
    )
    db.add(pattern)
    db.commit()
    db.refresh(pattern)
    return pattern


@router.put("/scam-patterns/{id}", response_model=ScamPatternResponse)
def update_scam_pattern(id: int, payload: ScamPatternCreateRequest, db: Session = Depends(get_db)):
    """Update an existing scam pattern by ID."""
    pattern = db.query(ScamPattern).filter(ScamPattern.id == id).first()
    if not pattern:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "detail": f"scam pattern id {id} does not exist"},
        )

    pattern.category = payload.category
    pattern.pattern = payload.pattern
    pattern.weight = payload.weight
    pattern.source_note = payload.source_note
    db.commit()
    db.refresh(pattern)
    return pattern


@router.delete("/scam-patterns/{id}", status_code=204)
def delete_scam_pattern(id: int, db: Session = Depends(get_db)):
    """Delete a scam pattern by ID."""
    pattern = db.query(ScamPattern).filter(ScamPattern.id == id).first()
    if not pattern:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "detail": f"scam pattern id {id} does not exist"},
        )
    db.delete(pattern)
    db.commit()
    return None
