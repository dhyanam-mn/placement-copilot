from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from models import Skill
from schemas import SkillCreateRequest, SkillResponse

router = APIRouter(tags=["Skills"])


@router.get("/skills", response_model=List[SkillResponse])
def list_skills(db: Session = Depends(get_db)):
    """List all registered skills in the system."""
    return db.query(Skill).order_by(Skill.id.asc()).all()


@router.get("/skills/{id}", response_model=SkillResponse)
def get_skill_by_id(id: int, db: Session = Depends(get_db)):
    """Get skill details by ID."""
    skill = db.query(Skill).filter(Skill.id == id).first()
    if not skill:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "detail": f"skill id {id} does not exist"},
        )
    return skill


@router.post("/skills", response_model=SkillResponse, status_code=201)
def create_skill(payload: SkillCreateRequest, db: Session = Depends(get_db)):
    """Create a new skill entry with optional category and aliases."""
    existing = db.query(Skill).filter(Skill.name == payload.name).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail={"error": "duplicate_skill", "detail": f"skill '{payload.name}' already exists"},
        )

    skill = Skill(
        name=payload.name,
        category=payload.category,
        aliases=payload.aliases or [],
    )
    db.add(skill)
    db.commit()
    db.refresh(skill)
    return skill


@router.put("/skills/{id}", response_model=SkillResponse)
def update_skill(id: int, payload: SkillCreateRequest, db: Session = Depends(get_db)):
    """Update skill details by ID."""
    skill = db.query(Skill).filter(Skill.id == id).first()
    if not skill:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "detail": f"skill id {id} does not exist"},
        )

    skill.name = payload.name
    skill.category = payload.category
    skill.aliases = payload.aliases or []
    db.commit()
    db.refresh(skill)
    return skill


@router.delete("/skills/{id}", status_code=204)
def delete_skill(id: int, db: Session = Depends(get_db)):
    """Delete a skill by ID."""
    skill = db.query(Skill).filter(Skill.id == id).first()
    if not skill:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "detail": f"skill id {id} does not exist"},
        )
    db.delete(skill)
    db.commit()
    return None
