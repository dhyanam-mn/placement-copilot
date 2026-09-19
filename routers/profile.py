from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from models import Profile, ProfileProject
from schemas import (
    ProfileCreateRequest,
    ProfileImportRequest,
    ProfileProjectCreateRequest,
    ProfileProjectResponse,
    ProfileResponse,
)

router = APIRouter(tags=["Profile"])


@router.get("/profile", response_model=ProfileResponse)
def get_profile(db: Session = Depends(get_db)):
    """Get candidate profile including project bullet items."""
    profile = db.query(Profile).order_by(Profile.id.asc()).first()
    if not profile:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "detail": "No profile record found"},
        )
    return profile


@router.post("/profile", response_model=ProfileResponse, status_code=201)
@router.put("/profile", response_model=ProfileResponse)
def create_or_update_profile(payload: ProfileCreateRequest, db: Session = Depends(get_db)):
    """Create or update candidate profile details."""
    profile = db.query(Profile).order_by(Profile.id.asc()).first()
    if not profile:
        profile = Profile(
            name=payload.name,
            email=payload.email,
            contact_info=payload.contact_info,
        )
        db.add(profile)
    else:
        profile.name = payload.name
        profile.email = payload.email
        profile.contact_info = payload.contact_info

    db.commit()
    db.refresh(profile)
    return profile


@router.get("/profile/projects", response_model=List[ProfileProjectResponse])
def get_profile_projects(db: Session = Depends(get_db)):
    """List candidate profile project bullets."""
    return db.query(ProfileProject).order_by(ProfileProject.id.asc()).all()


@router.post("/profile/projects", response_model=ProfileProjectResponse, status_code=201)
def create_profile_project(payload: ProfileProjectCreateRequest, db: Session = Depends(get_db)):
    """Add a new project bullet to the candidate profile."""
    profile = db.query(Profile).order_by(Profile.id.asc()).first()
    if not profile:
        profile = Profile(name="Default Candidate", email="candidate@example.com")
        db.add(profile)
        db.commit()
        db.refresh(profile)

    project = ProfileProject(
        profile_id=profile.id,
        project_name=payload.project_name,
        bullet_text=payload.bullet_text,
        skill_tags=payload.skill_tags or [],
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.put("/profile/projects/{id}", response_model=ProfileProjectResponse)
def update_profile_project(id: int, payload: ProfileProjectCreateRequest, db: Session = Depends(get_db)):
    """Update an existing profile project bullet by ID."""
    project = db.query(ProfileProject).filter(ProfileProject.id == id).first()
    if not project:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "detail": f"profile project id {id} does not exist"},
        )
    project.project_name = payload.project_name
    project.bullet_text = payload.bullet_text
    project.skill_tags = payload.skill_tags or []
    db.commit()
    db.refresh(project)
    return project


@router.delete("/profile/projects/{id}", status_code=204)
def delete_profile_project(id: int, db: Session = Depends(get_db)):
    """Delete a profile project bullet by ID."""
    project = db.query(ProfileProject).filter(ProfileProject.id == id).first()
    if not project:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "detail": f"profile project id {id} does not exist"},
        )
    db.delete(project)
    db.commit()
    return None


@router.post("/profile/import", response_model=ProfileResponse)
def import_profile(payload: ProfileImportRequest, db: Session = Depends(get_db)):
    """Import and overwrite profile & projects from validated JSON payload."""
    profile = db.query(Profile).order_by(Profile.id.asc()).first()
    if not profile:
        profile = Profile(
            name=payload.name,
            email=payload.email,
            contact_info=payload.contact_info,
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)
    else:
        profile.name = payload.name
        profile.email = payload.email
        profile.contact_info = payload.contact_info
        # Remove existing projects for clean overwrite
        db.query(ProfileProject).filter(ProfileProject.profile_id == profile.id).delete()

    for p in payload.projects:
        project = ProfileProject(
            profile_id=profile.id,
            project_name=p.project_name,
            bullet_text=p.bullet_text,
            skill_tags=p.skill_tags or [],
        )
        db.add(project)

    db.commit()
    db.refresh(profile)
    return profile
