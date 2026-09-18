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

    model_config = ConfigDict(from_attributes=True)


class ApplicationListResponse(BaseModel):
    applications: List[ApplicationResponse]


class ApplicationCreateRequest(BaseModel):
    company: str
    role: str
    jd_text: str
    source: Literal['serpapi', 'unstop']


class ApplicationStatusPatchRequest(BaseModel):
    status: ApplicationStatus
    status_source: Optional[StatusSourceType] = None


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
    risk_score: float
    flagged_reasons: List[str]
    explanation_text: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# --- Prep Schemas ---

class PrepEvaluateRequest(BaseModel):
    question: str
    student_answer: str
    question_tags: List[str]


class PrepEvaluateResponse(BaseModel):
    keyword_coverage: float
    feedback_text: str
    flagged_as_weak: bool


# --- Standard Error Schema ---

class ErrorResponse(BaseModel):
    error: str
    detail: str
