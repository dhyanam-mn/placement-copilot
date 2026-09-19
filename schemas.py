from typing import Any, Dict, List, Literal, Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict

ApplicationStatus = Literal[
    'DISCOVERED',
    'READY_TO_APPLY',
    'APPLIED',
    'OA_INVITE',
    'INTERVIEW',
    'REJECTED',
    'GHOSTED',
    'OFFER',
]

StatusSourceType = Literal['gmail_auto', 'auto_ghost', 'manual']


# --- Application Schemas ---

class ApplicationResponse(BaseModel):
    id: int
    company: str
    role: str
    source: str
    status: ApplicationStatus
    status_source: Optional[StatusSourceType] = None
    match_score: Optional[float] = None
    tailored_resume_id: Optional[int] = None
    gap_report_id: Optional[int] = None
    last_contact_date: datetime
    last_updated: datetime
    created_at: datetime
    is_demo: bool = False

    model_config = ConfigDict(from_attributes=True)


class ApplicationListResponse(BaseModel):
    applications: List[ApplicationResponse]


class ApplicationCreateRequest(BaseModel):
    company: str
    role: str
    jd_text: str
    source: Literal['adzuna', 'greenhouse', 'lever', 'unstop']


class ApplicationStatusPatchRequest(BaseModel):
    status: ApplicationStatus
    status_source: Optional[StatusSourceType] = None


# --- Status Event Schemas ---

class StatusEventResponse(BaseModel):
    id: int
    application_id: int
    old_status: Optional[str] = None
    new_status: str
    event_source: Optional[str] = None
    created_at: datetime
    is_demo: bool = False

    model_config = ConfigDict(from_attributes=True)


class StatusEventListResponse(BaseModel):
    events: List[StatusEventResponse]


# --- Notification Schemas ---

class NotificationResponse(BaseModel):
    id: int
    type: str
    content: str
    read: bool
    created_at: datetime
    is_demo: bool = False

    model_config = ConfigDict(from_attributes=True)


class NotificationListResponse(BaseModel):
    notifications: List[NotificationResponse]


# --- Tailoring Schemas ---

class BulletScore(BaseModel):
    project: str
    bullet: str
    score: float


class TailoredResumeData(BaseModel):
    ordered_bullets: List[BulletScore]


class TailorResponse(BaseModel):
    tailored_resume_id: int
    resume_data: TailoredResumeData


# --- Gap Report Schemas ---

class GapReportResponse(BaseModel):
    id: int
    application_id: Optional[int] = None
    report_type: Literal['per_row', 'aggregate']
    summary_text: str
    details: Optional[Dict[str, Any]] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Scam Check Schemas ---

class ScamCheckRequest(BaseModel):
    recruiter_name: Optional[str] = None
    recruiter_domain: Optional[str] = None
    claimed_company: Optional[str] = None


class ScamCheckResponse(BaseModel):
    id: int
    application_id: Optional[int] = None
    recruiter_name: Optional[str] = None
    recruiter_domain: Optional[str] = None
    risk_score: float
    flagged_reasons: List[str]
    explanation_text: Optional[str] = None
    created_at: datetime
    is_demo: bool = False

    model_config = ConfigDict(from_attributes=True)


# --- Prep Schemas ---

class PrepRecommendationItem(BaseModel):
    id: int
    application_id: int
    resource_id: int
    title: str
    url: str
    reason: str
    est_hours: Optional[int] = 3
    created_at: Optional[str] = None


class PrepResponse(BaseModel):
    application_id: int
    recommendations: List[PrepRecommendationItem]


# --- Profile & Project Schemas ---

class ProfileProjectCreateRequest(BaseModel):
    project_name: str
    bullet_text: str
    skill_tags: Optional[List[str]] = None


class ProfileProjectResponse(BaseModel):
    id: int
    profile_id: int
    project_name: str
    bullet_text: str
    skill_tags: Optional[List[str]] = None
    created_at: datetime
    is_demo: bool = False

    model_config = ConfigDict(from_attributes=True)


class ProfileCreateRequest(BaseModel):
    name: str
    email: Optional[str] = None
    contact_info: Optional[str] = None


class ProfileResponse(BaseModel):
    id: int
    name: str
    email: Optional[str] = None
    contact_info: Optional[str] = None
    created_at: datetime
    is_demo: bool = False
    projects: List[ProfileProjectResponse] = []

    model_config = ConfigDict(from_attributes=True)


class ProfileImportRequest(BaseModel):
    name: str
    email: Optional[str] = None
    contact_info: Optional[str] = None
    projects: List[ProfileProjectCreateRequest] = []


# --- Resource & Skill Schemas ---

class ResourceSkillLink(BaseModel):
    skill_name: str
    weight: float = 1.0

    model_config = ConfigDict(from_attributes=True)


class ResourceCreateRequest(BaseModel):
    title: str
    url: str
    is_active: bool = True
    skills: Optional[List[ResourceSkillLink]] = []


class ResourceResponse(BaseModel):
    id: int
    title: str
    url: str
    is_active: bool
    verified_at: Optional[datetime] = None
    created_at: datetime
    is_demo: bool = False
    skills: List[ResourceSkillLink] = []

    model_config = ConfigDict(from_attributes=True)


class SkillCreateRequest(BaseModel):
    name: str
    category: Optional[str] = None
    aliases: Optional[List[str]] = []


class SkillResponse(BaseModel):
    id: int
    name: str
    category: Optional[str] = None
    aliases: Optional[List[str]] = None
    created_at: datetime
    is_demo: bool = False

    model_config = ConfigDict(from_attributes=True)


# --- Scam Pattern Schemas ---

class ScamPatternCreateRequest(BaseModel):
    category: str
    pattern: str
    weight: float
    source_note: str = 'TODO'


class ScamPatternResponse(BaseModel):
    id: int
    category: str
    pattern: str
    weight: float
    source_note: str
    created_at: datetime
    is_demo: bool = False

    model_config = ConfigDict(from_attributes=True)


# --- Watchlist Schemas ---

class WatchlistCreateRequest(BaseModel):
    company: str
    ats: Optional[str] = None
    token: Optional[str] = None
    active: bool = True


class WatchlistResponse(BaseModel):
    id: int
    company: str
    ats: Optional[str] = None
    token: Optional[str] = None
    active: bool
    created_at: datetime
    is_demo: bool = False

    model_config = ConfigDict(from_attributes=True)


# --- Setting Schemas ---

class SettingCreateRequest(BaseModel):
    key: str
    value: Any


class SettingResponse(BaseModel):
    key: str
    value: Any
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Health Schema ---

class HealthStatusResponse(BaseModel):
    status: str
    services: Dict[str, str]


# --- Standard Error Schema ---

class ErrorResponse(BaseModel):
    error: str
    detail: str
