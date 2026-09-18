from fastapi import APIRouter
from schemas import (
    LLMGenerateRequest,
    PrepEvaluateRequest,
    PrepEvaluateResponse,
)
from routes.generate import llm_generate

router = APIRouter(prefix="/prep", tags=["Prep"])


def _stem(word: str) -> str:
    """Lightweight suffix strip for common English verb/plural forms."""
    for suffix in ("ing", "ed", "es", "s"):
        if word.endswith(suffix) and len(word) > len(suffix) + 2:
            return word[: -len(suffix)]
    return word


def _matches_tag(tag: str, text_lower: str) -> bool:
    """
    Check if a tag matches in the text.
    Handles exact substring match or stem-level presence for multi-word phrases.
    """
    tag_clean = tag.lower().strip()
    if tag_clean in text_lower:
        return True
    words = [_stem(w) for w in tag_clean.split()]
    return bool(words) and all(w in text_lower for w in words)


@router.post("/evaluate-answer", response_model=PrepEvaluateResponse)
async def evaluate_answer(payload: PrepEvaluateRequest) -> PrepEvaluateResponse:
    """
    Evaluate student interview answer for the Prep Agent's feedback loop.

    1. First does a fast, cheap deterministic check for keyword overlap (no LLM call).
    2. Then calls the internal /llm-generate logic with task_type 'answer_feedback' to get qualitative feedback.
    3. Returns keyword_coverage (float 0-1), feedback_text (string), and flagged_as_weak (bool, true if coverage < 0.3).
    """
    # Step 1: Cheap deterministic keyword presence check (computed BEFORE any LLM call)
    student_ans_lower = payload.student_answer.lower()
    total_tags = len(payload.question_tags)

    matched_tags = []
    for tag in payload.question_tags:
        if _matches_tag(tag, student_ans_lower):
            matched_tags.append(tag)

    if total_tags > 0:
        keyword_coverage = round(len(matched_tags) / total_tags, 2)
    else:
        keyword_coverage = 1.0

    flagged_as_weak = bool(keyword_coverage < 0.3)

    # Step 2: Call internal /llm-generate logic with task_type "answer_feedback"
    llm_request = LLMGenerateRequest(
        task_type="answer_feedback",
        context={
            "question": payload.question,
            "student_answer": payload.student_answer,
            "expected_topics": payload.question_tags,
        },
    )

    llm_response = await llm_generate(llm_request)

    # Step 3: Handle feedback text fallback if LLM is unavailable
    if llm_response.error == "llm_unavailable" or not llm_response.generated_text:
        feedback_text = f"Keyword coverage: {keyword_coverage}. LLM feedback unavailable."
    else:
        feedback_text = llm_response.generated_text

    # Step 4: Return combined evaluation result
    return PrepEvaluateResponse(
        keyword_coverage=keyword_coverage,
        feedback_text=feedback_text,
        flagged_as_weak=flagged_as_weak,
    )
