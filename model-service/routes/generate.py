from fastapi import APIRouter
from schemas import LLMGenerateRequest, LLMGenerateResponse

router = APIRouter(tags=["LLM Generate"])


def _generate_placeholder_text(task_type: str, context: dict) -> str:
    """
    Generate contextual placeholder text matching the contract format
    for the 3 supported LLM task types.
    """
    if task_type == "scam_explanation":
        flagged_reasons = context.get("flagged_reasons", [])
        recruiter_info = context.get("recruiter_info", {})
        claimed_company = recruiter_info.get("claimed_company", "the company")

        if flagged_reasons:
            reasons_summary = ", and ".join(flagged_reasons)
            return (
                f"This looks risky: {reasons_summary}. "
                f"Exercise caution before sharing personal data or proceeding with {claimed_company}."
            )
        return (
            f"This looks risky: the sender's email domain doesn't match {claimed_company}'s official domain, "
            "and asking for a processing fee before any interview is a common red flag."
        )

    elif task_type == "answer_feedback":
        expected_topics = context.get("expected_topics", [])
        if expected_topics:
            highlight = expected_topics[0]
            return (
                f"Good coverage of key concepts — you explained your approach clearly. "
                f"To strengthen your answer, explicitly emphasize '{highlight}' directly."
            )
        return (
            "Good coverage of tiling and thresholding — you didn't explicitly name "
            "'hard negative mining' itself, worth stating the term directly."
        )

    elif task_type == "gap_summary":
        rejected = context.get("rejected_applications", [])
        if rejected:
            roles = list({item.get("role_tag") for item in rejected if "role_tag" in item})
            role_str = "/".join(roles) if roles else "target"
            return (
                f"You are consistently advancing past resume screening but facing bottlenecks "
                f"during technical assessments for {role_str} roles."
            )
        return (
            "You are consistently advancing past resume screening but facing bottlenecks "
            "during the Online Assessment stage for SDE roles."
        )

    return "Placeholder generation response."


@router.post("/llm-generate", response_model=LLMGenerateResponse)
async def llm_generate(payload: LLMGenerateRequest) -> LLMGenerateResponse:
    """
    Generate LLM text for one of the three supported task types:
    - scam_explanation
    - answer_feedback
    - gap_summary

    Returns placeholder text conforming to MODEL_SERVICE_CONTRACT.md.
    """
    generated_text = _generate_placeholder_text(payload.task_type, payload.context)

    return LLMGenerateResponse(
        generated_text=generated_text,
        task_type=payload.task_type,
    )
