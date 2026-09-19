from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from models import Setting
from schemas import SettingCreateRequest, SettingResponse

router = APIRouter(tags=["Settings"])


@router.get("/settings", response_model=List[SettingResponse])
def list_settings(db: Session = Depends(get_db)):
    """List all system settings."""
    return db.query(Setting).order_by(Setting.key.asc()).all()


@router.get("/settings/{key}", response_model=SettingResponse)
def get_setting_by_key(key: str, db: Session = Depends(get_db)):
    """Get system setting by key."""
    setting = db.query(Setting).filter(Setting.key == key).first()
    if not setting:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "detail": f"setting key '{key}' does not exist"},
        )
    return setting


@router.post("/settings", response_model=SettingResponse, status_code=201)
@router.put("/settings/{key}", response_model=SettingResponse)
def create_or_update_setting(payload: SettingCreateRequest, key: str = None, db: Session = Depends(get_db)):
    """Create or update a system setting value."""
    target_key = key or payload.key
    setting = db.query(Setting).filter(Setting.key == target_key).first()
    if not setting:
        setting = Setting(key=target_key, value=payload.value)
        db.add(setting)
    else:
        setting.value = payload.value

    db.commit()
    db.refresh(setting)

    # Invalidate settings_service cache
    from services.settings_service import clear_settings_cache
    clear_settings_cache()

    return setting
