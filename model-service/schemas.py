from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


# ==========================================
# /health Schemas
# ==========================================

class HealthResponse(BaseModel):
    status: str = Field(default="ok", description="Service health status")
    model_loaded: bool = Field(
        default=True,
        description="False until embedding model finishes loading at startup; backend treats false as not ready yet",
    )


# ==========================================
# /embed Schemas
# ==========================================

class EmbedRequest(BaseModel):
    texts: List[str] = Field(
        ...,
        description="List of strings to embed (1-50 items, non-empty strings)",
    )


class EmbedResponse(BaseModel):
    embeddings: List[List[float]] = Field(
        ...,
        description="List of 384-dimensional float embeddings corresponding 1-to-1 to input texts",
    )
    model_name: str = Field(
        default="all-MiniLM-L6-v2",
        description="Embedding model name",
    )
    dimension: int = Field(
        default=384,
        description="Embedding vector dimensionality",
    )


class ErrorResponse(BaseModel):
    error: str = Field(..., description="Error identifier code")
    detail: Optional[str] = Field(None, description="Detailed explanation of the error")


# ==========================================
# /llm-generate Schemas
# ==========================================

TaskType = Literal["scam_explanation", "answer_feedback", "gap_summary"]


class RecruiterInfo(BaseModel):
    name: Optional[str] = None
    claimed_company: Optional[str] = None
    email_domain: Optional[str] = None


class ScamExplanationContext(BaseModel):
    flagged_reasons: List[str]
    recruiter_info: Optional[RecruiterInfo] = None


class AnswerFeedbackContext(BaseModel):
    question: str
    student_answer: str
    expected_topics: List[str] = Field(default_factory=list)


class RejectedApplication(BaseModel):
    role_tag: str
    rejection_stage: str


class GapSummaryContext(BaseModel):
    rejected_applications: List[RejectedApplication]


class LLMGenerateRequest(BaseModel):
    task_type: TaskType = Field(
        ...,
        description="One of 'scam_explanation', 'answer_feedback', 'gap_summary'",
    )
    context: Dict[str, Any] = Field(
        ...,
        description="Task context containing relevant inputs for generation",
    )


class LLMGenerateResponse(BaseModel):
    generated_text: str = Field(..., description="Generated text from LLM or fallback")
    task_type: str = Field(..., description="Task type corresponding to the request")
    error: Optional[str] = Field(
        None,
        description="Optional error indicator (e.g. 'llm_unavailable' if LLM is unreachable or timed out)",
    )


# ==========================================
# /prep/evaluate-answer Schemas
# ==========================================

class PrepEvaluateRequest(BaseModel):
    question: str = Field(..., description="Interview question")
    student_answer: str = Field(..., description="Answer provided by student")
    question_tags: List[str] = Field(
        ...,
        description="List of expected keywords/topics to evaluate against",
    )


class PrepEvaluateResponse(BaseModel):
    keyword_coverage: float = Field(
        ...,
        description="Fraction of question_tags found in student_answer (0.0 to 1.0)",
    )
    feedback_text: str = Field(
        ...,
        description="Constructive feedback on the answer",
    )
    flagged_as_weak: bool = Field(
        ...,
        description="True if keyword_coverage < 0.3",
    )
