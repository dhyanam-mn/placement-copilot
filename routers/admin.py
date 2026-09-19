from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Any
from pydantic import BaseModel, ConfigDict
import models
from database import get_db

router = APIRouter(prefix="/admin", tags=["Admin"])

# Schemas
class SettingSchema(BaseModel):
    key: str
    value: Any
    model_config = ConfigDict(from_attributes=True)

class ProfileSchema(BaseModel):
    id: int
    name: str
    contact_info: str | None
    email: str | None
    is_demo: bool
    model_config = ConfigDict(from_attributes=True)

class ResourceSchema(BaseModel):
    id: int
    title: str
    url: str
    is_demo: bool
    model_config = ConfigDict(from_attributes=True)

class ScamPatternSchema(BaseModel):
    id: int
    category: str
    pattern: str
    weight: float
    source_note: str
    is_demo: bool
    model_config = ConfigDict(from_attributes=True)

class WatchlistSchema(BaseModel):
    id: int
    company: str
    ats: str | None
    token: str | None
    active: bool
    is_demo: bool
    model_config = ConfigDict(from_attributes=True)

# Settings
@router.get("/settings", response_model=List[SettingSchema])
def get_settings(db: Session = Depends(get_db)):
    return db.query(models.Setting).all()

# Profile
@router.get("/profile", response_model=List[ProfileSchema])
def get_profiles(db: Session = Depends(get_db)):
    return db.query(models.Profile).all()

# Resources
@router.get("/resources", response_model=List[ResourceSchema])
def get_resources(db: Session = Depends(get_db)):
    return db.query(models.Resource).all()

# Scam Patterns
@router.get("/scam_patterns", response_model=List[ScamPatternSchema])
def get_scam_patterns(db: Session = Depends(get_db)):
    return db.query(models.ScamPattern).all()

# Watchlist
@router.get("/watchlist", response_model=List[WatchlistSchema])
def get_watchlist(db: Session = Depends(get_db)):
    return db.query(models.CompanyWatchlist).all()
