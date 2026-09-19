from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from database import get_db
from models import Resource, ResourceSkill, Skill
from schemas import (
    ResourceCreateRequest,
    ResourceResponse,
    ResourceSkillLink,
)

router = APIRouter(tags=["Resources"])


@router.get("/resources", response_model=List[ResourceResponse])
def list_resources(db: Session = Depends(get_db)):
    """List all learning resources including associated skill links."""
    return db.query(Resource).order_by(Resource.id.asc()).all()


@router.get("/resources/{id}", response_model=ResourceResponse)
def get_resource_by_id(id: int, db: Session = Depends(get_db)):
    """Get learning resource details by ID."""
    res = db.query(Resource).filter(Resource.id == id).first()
    if not res:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "detail": f"resource id {id} does not exist"},
        )
    return res


@router.post("/resources", response_model=ResourceResponse, status_code=201)
def create_resource(payload: ResourceCreateRequest, db: Session = Depends(get_db)):
    """Create a new learning resource with skill links."""
    resource = Resource(
        title=payload.title,
        url=payload.url,
        is_active=payload.is_active,
    )
    db.add(resource)
    db.commit()
    db.refresh(resource)

    if payload.skills:
        for sk in payload.skills:
            # Ensure target skill exists in skills table
            skill_obj = db.query(Skill).filter(Skill.name == sk.skill_name).first()
            if not skill_obj:
                skill_obj = Skill(name=sk.skill_name)
                db.add(skill_obj)
                db.commit()

            rs = ResourceSkill(
                resource_id=resource.id,
                skill_name=sk.skill_name,
                weight=sk.weight,
            )
            db.add(rs)
        db.commit()
        db.refresh(resource)

    return resource


@router.put("/resources/{id}", response_model=ResourceResponse)
def update_resource(id: int, payload: ResourceCreateRequest, db: Session = Depends(get_db)):
    """Update an existing learning resource and its skill links."""
    resource = db.query(Resource).filter(Resource.id == id).first()
    if not resource:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "detail": f"resource id {id} does not exist"},
        )

    resource.title = payload.title
    resource.url = payload.url
    resource.is_active = payload.is_active

    # Re-link skills
    db.query(ResourceSkill).filter(ResourceSkill.resource_id == id).delete()
    if payload.skills:
        for sk in payload.skills:
            skill_obj = db.query(Skill).filter(Skill.name == sk.skill_name).first()
            if not skill_obj:
                skill_obj = Skill(name=sk.skill_name)
                db.add(skill_obj)
                db.commit()

            rs = ResourceSkill(
                resource_id=resource.id,
                skill_name=sk.skill_name,
                weight=sk.weight,
            )
            db.add(rs)

    db.commit()
    db.refresh(resource)
    return resource


@router.delete("/resources/{id}", status_code=204)
def delete_resource(id: int, db: Session = Depends(get_db)):
    """Delete a learning resource by ID."""
    resource = db.query(Resource).filter(Resource.id == id).first()
    if not resource:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "detail": f"resource id {id} does not exist"},
        )
    db.delete(resource)
    db.commit()
    return None


@router.post("/resources/check-links")
def trigger_resource_link_check():
    """Trigger URL HEAD checks for all learning resources and update verified_at/is_active flags."""
    from scripts.check_links import run_link_check
    results = run_link_check()
    return results
