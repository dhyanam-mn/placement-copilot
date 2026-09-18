from typing import Dict, List, Any
from fastapi import APIRouter
from schemas import (
    LLMGenerateRequest,
    PrepEvaluateRequest,
    PrepEvaluateResponse,
    ResourceItem,
)
from routes.generate import llm_generate

router = APIRouter(prefix="/prep", tags=["Prep"])

# Curated Technical Skill Resources Mapping
RESOURCE_DATABASE: Dict[str, Dict[str, str]] = {
    "dsa": {
        "title": "GeeksforGeeks Data Structures & Algorithms Roadmap",
        "url": "https://www.geeksforgeeks.org/data-structures/",
    },
    "hard negative mining": {
        "title": "PyTorch Vision Hard Negative Mining & Object Detection Tutorial",
        "url": "https://pytorch.org/tutorials/intermediate/torchvision_tutorial.html",
    },
    "sliding window tiling": {
        "title": "Rasterio Windowed I/O & Drone Tiling Guide",
        "url": "https://rasterio.readthedocs.io/en/stable/topics/windowed-rw.html",
    },
    "system design": {
        "title": "System Design Primer by Donne Martin",
        "url": "https://github.com/donnemartin/system-design-primer",
    },
    "sql": {
        "title": "PostgreSQL Official SQL Tutorial & Performance Tuning",
        "url": "https://www.postgresql.org/docs/current/tutorial.html",
    },
    "fastapi": {
        "title": "FastAPI Official Documentation & Async Best Practices",
        "url": "https://fastapi.tiangolo.com/tutorial/",
    },
    "pytorch": {
        "title": "PyTorch Official Tutorials & Deep Learning Fundamentals",
        "url": "https://pytorch.org/tutorials/",
    },
    "yolov8": {
        "title": "Ultralytics YOLOv8 Architecture & Training Docs",
        "url": "https://docs.ultralytics.com/",
    },
    "redis": {
        "title": "Redis University - Caching Patterns & Distributed Locks",
        "url": "https://redis.io/docs/manual/client-side-caching/",
    },
    "postgresql": {
        "title": "Use The Index, Luke! Database Performance Guide",
        "url": "https://use-the-index-luke.com/",
    },
    "react": {
        "title": "React Official Docs & Modern State Management",
        "url": "https://react.dev/learn",
    },
}


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
    2. Maps question tags to curated learning resource links & actionable suggestions.
    3. Calls the internal /llm-generate logic with task_type 'answer_feedback' to get qualitative feedback.
    4. Returns keyword_coverage, feedback_text, flagged_as_weak, recommended_resources, and actionable_suggestions.
    """
    # Step 1: Cheap deterministic keyword presence check
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

    flagged_as_weak = bool(keyword_coverage < 0.3)

    # Step 2: Build recommended learning resources & actionable suggestions
    recommended_resources: List[ResourceItem] = []
    actionable_suggestions: List[str] = []

    # Map missing and question tags to resources
    for tag in payload.question_tags:
        tag_key = tag.lower().strip()
        if tag_key in RESOURCE_DATABASE:
            res_info = RESOURCE_DATABASE[tag_key]
            recommended_resources.append(
                ResourceItem(skill=tag, title=res_info["title"], url=res_info["url"])
            )

    # Fallback generic resources if none specific matched
    if not recommended_resources:
        recommended_resources.append(
            ResourceItem(
                skill="General CS / System Design",
                title="System Design Primer & Technical Interview Prep Guide",
                url="https://github.com/donnemartin/system-design-primer",
            )
        )

    # Actionable suggestions based on missing tags
    if missing_tags:
        missing_str = ", ".join(f"'{m}'" for m in missing_tags)
        actionable_suggestions.append(
            f"Explicitly mention technical terms {missing_str} in your oral response."
        )
        actionable_suggestions.append(
            "Structure your answer using STAR technique (Situation, Task, Action, Result) with precise metrics."
        )
    else:
        actionable_suggestions.append(
            "Great topic coverage! Focus on articulating trade-offs (e.g. latency vs accuracy) for higher-level interviews."
        )

    # Step 3: Call internal /llm-generate logic with task_type "answer_feedback"
    llm_request = LLMGenerateRequest(
        task_type="answer_feedback",
        context={
            "question": payload.question,
            "student_answer": payload.student_answer,
            "expected_topics": payload.question_tags,
        },
    )

    llm_response = await llm_generate(llm_request)

    # Step 4: Handle feedback text fallback if LLM is unavailable
    if llm_response.error == "llm_unavailable" or not llm_response.generated_text:
        feedback_text = f"Keyword coverage: {keyword_coverage}. LLM feedback unavailable."
    else:
        feedback_text = llm_response.generated_text

    # Step 5: Return combined evaluation result
    return PrepEvaluateResponse(
        keyword_coverage=keyword_coverage,
        feedback_text=feedback_text,
        flagged_as_weak=flagged_as_weak,
        recommended_resources=recommended_resources,
        actionable_suggestions=actionable_suggestions,
    )
