import logging
import time
from typing import Any, Dict, Optional
from sqlalchemy.orm import Session
from models import Setting

logger = logging.getLogger("placement_copilot.settings_service")

# In-memory settings cache with TTL
_SETTINGS_CACHE: Dict[str, Any] = {}
_CACHE_TIMESTAMP: float = 0.0
_CACHE_TTL_SECONDS: float = 60.0

DEFAULTS = {
    "ghost_days": 45,
    "nudge_days": 14,
    "scam_threshold": 0.75,
    "scout_interval_hours": 6,
}


def clear_settings_cache():
    """Invalidate in-memory settings cache."""
    global _SETTINGS_CACHE, _CACHE_TIMESTAMP
    _SETTINGS_CACHE = {}
    _CACHE_TIMESTAMP = 0.0


def refresh_settings_cache(db: Session) -> Dict[str, Any]:
    """Force-reload all settings from the database into the cache, seeding missing defaults."""
    global _SETTINGS_CACHE, _CACHE_TIMESTAMP
    try:
        db_settings = db.query(Setting).all()
        existing_keys = {s.key: s.value for s in db_settings}

        # Seed defaults if missing in DB
        missing = False
        for key, def_val in DEFAULTS.items():
            if key not in existing_keys:
                db_val = def_val if isinstance(def_val, (dict, list)) else {"val": def_val}
                setting_rec = Setting(key=key, value=db_val)
                db.add(setting_rec)
                existing_keys[key] = db_val
                missing = True

        if missing:
            db.commit()

        # Unwrap stored JSON dict values if needed
        unwrapped = {}
        for k, v in existing_keys.items():
            if isinstance(v, dict) and "val" in v:
                unwrapped[k] = v["val"]
            else:
                unwrapped[k] = v

        _SETTINGS_CACHE = unwrapped
        _CACHE_TIMESTAMP = time.time()
    except Exception as e:
        logger.error(f"Error loading settings from DB: {e}")

    return _SETTINGS_CACHE


def get_setting(db: Session, key: str, default: Any = None, force_refresh: bool = False) -> Any:
    """Get a setting value by key, reading from cache if fresh or loading from DB."""
    global _SETTINGS_CACHE, _CACHE_TIMESTAMP
    now = time.time()
    if force_refresh or not _SETTINGS_CACHE or (now - _CACHE_TIMESTAMP > _CACHE_TTL_SECONDS):
        refresh_settings_cache(db)

    if key in _SETTINGS_CACHE:
        return _SETTINGS_CACHE[key]
    
    if key in DEFAULTS:
        return DEFAULTS[key]

    return default


def get_ghost_days(db: Session) -> int:
    val = get_setting(db, "ghost_days", DEFAULTS["ghost_days"])
    try:
        return int(val)
    except (ValueError, TypeError):
        return 45


def get_nudge_days(db: Session) -> int:
    val = get_setting(db, "nudge_days", DEFAULTS["nudge_days"])
    try:
        return int(val)
    except (ValueError, TypeError):
        return 14


def get_scam_threshold(db: Session) -> float:
    val = get_setting(db, "scam_threshold", DEFAULTS["scam_threshold"])
    try:
        return float(val)
    except (ValueError, TypeError):
        return 0.75


def get_scout_interval_hours(db: Session) -> int:
    val = get_setting(db, "scout_interval_hours", DEFAULTS["scout_interval_hours"])
    try:
        return int(val)
    except (ValueError, TypeError):
        return 6
