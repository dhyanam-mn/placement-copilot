from fastapi import APIRouter
from schemas import PrepEvaluateRequest, PrepEvaluateResponse

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
    Handles exact substring match or stem-level presence for multi-word phrases
    (e.g., 'confidence thresholding' matches 'confidence thresholds').
    """
    tag_clean = tag.lower().strip()
    if tag_clean in text_lower:
        return True
    words = [_stem(w) for w in tag_clean.split()]
    return bool(words) and all(w in text_lower for w in words)


@router.post("/evaluate-answer", response_model=PrepEvaluateResponse)
async def evaluate_answer(payload: PrepEvaluateRequest) -> PrepEvaluateResponse:
    """
    Evaluate student interview answer.
    Combines deterministic keyword coverage with feedback generation.
    - keyword_coverage: fraction of question_tags found (case-insensitive substring match) in student_answer.
    - flagged_as_weak: true if keyword_coverage < 0.3.
    - feedback_text: constructive feedback highlighting matched and missing concepts.
    """
    student_ans_lower = payload.student_answer.lower()
    total_tags = len(payload.question_tags)

    matched_tags = []
    missing_tags = []

    for tag in payload.question_tags:
        if _matches_tag(tag, student_ans_lower):
            matched_tags.append(tag)
        else:
            missing_tags.append(tag)

    if total_tags > 0:
        keyword_coverage = round(len(matched_tags) / total_tags, 2)
    else:
        keyword_coverage = 1.0

    flagged_as_weak = keyword_coverage < 0.3

    # Generate constructive feedback text
    if missing_tags and matched_tags:
        feedback_text = (
            f"Good coverage of {', '.join(matched_tags)} — "
            f"you didn't explicitly name '{missing_tags[0]}' itself, worth stating the term directly."
        )
    elif not matched_tags and missing_tags:
        feedback_text = (
            f"Answer needs more technical depth. You didn't touch on key expected concepts "
            f"such as '{missing_tags[0]}'."
        )
    else:
        feedback_text = (
            "Comprehensive response! You directly covered all required technical topics and methodologies."
        )

    return PrepEvaluateResponse(
        keyword_coverage=keyword_coverage,
        feedback_text=feedback_text,
        flagged_as_weak=flagged_as_weak,
    )
