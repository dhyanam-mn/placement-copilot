import os
import logging
from typing import Any, Dict, List, Optional
import httpx
from fastapi import APIRouter
from schemas import LLMGenerateRequest, LLMGenerateResponse

router = APIRouter(tags=["LLM Generate"])
logger = logging.getLogger("uvicorn.info")

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
OLLAMA_TIMEOUT = float(os.getenv("OLLAMA_TIMEOUT", "10.0"))


def _generate_placeholder_text(task_type: str, context: dict) -> str:
    """
    Fallback deterministic text generator when Ollama is unreachable or times out.
    Conforms to MODEL_SERVICE_CONTRACT.md format.
    """
    if task_type == "scam_explanation":
        flagged_reasons = context.get("flagged_reasons", [])
        recruiter_info = context.get("recruiter_info", {})
        claimed_company = (
            recruiter_info.get("claimed_company")
            or recruiter_info.get("name")
            or "the company"
        )

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
            roles = list({item.get("role_tag") for item in rejected if isinstance(item, dict) and "role_tag" in item})
            role_str = "/".join(roles) if roles else "target"
            return (
                f"You are consistently advancing past resume screening but facing bottlenecks "
                f"during technical assessments for {role_str} roles."
            )
        return (
            "You are consistently advancing past resume screening but facing bottlenecks "
            "during the Online Assessment stage for SDE roles."
        )

    return "Fallback generation response."


def _build_prompt(task_type: str, context: dict) -> str:
    """
    Construct short, tightly-scoped prompt templates for Ollama based on task_type.
    """
    if task_type == "scam_explanation":
        flagged_reasons = context.get("flagged_reasons", [])
        recruiter_info = context.get("recruiter_info", {})

        reasons_text = (
            "\n".join([f"- {r}" for r in flagged_reasons])
            if flagged_reasons
            else "- Unverified outreach details"
        )
        sender_email = (
            recruiter_info.get("sender_email")
            or recruiter_info.get("email_domain")
            or "Unknown"
        )
        claimed_company = (
            recruiter_info.get("claimed_company")
            or recruiter_info.get("name")
            or "Unknown"
        )
        official_domain = recruiter_info.get("official_domain") or "Unknown"
        message_body = (
            recruiter_info.get("message_body") or recruiter_info.get("message") or ""
        )

        recruiter_details = (
            f"Sender Email: {sender_email}\n"
            f"Claimed Company: {claimed_company}\n"
            f"Official Domain: {official_domain}\n"
        )
        if message_body:
            recruiter_details += f"Message Content: {message_body}\n"

        return f"""You are Placement Copilot's Scam-Check Agent.
Write a clear 2-3 sentence plain-English explanation explaining why this recruiter outreach was flagged as fraudulent based ONLY on the given reasons.
Do NOT decide whether it's a scam (that is already decided by rule checks) — only explain the given reasons clearly.

Flagged Reasons:
{reasons_text}

Recruiter Information:
{recruiter_details}

Instructions:
- Write exactly 2-3 concise sentences explaining the red flags.
- Do NOT output any preamble, markdown headings, quotes, or conversational filler.
- Be direct, professional, and clear."""

    elif task_type == "answer_feedback":
        question = context.get("question", "")
        student_answer = context.get("student_answer", "")
        expected_topics = context.get("expected_topics", [])
        topics_str = (
            ", ".join(expected_topics)
            if expected_topics
            else "Key technical concepts"
        )

        return f"""You are an expert technical interviewer evaluating a student's answer.
Evaluate whether the answer covers the expected key topics and provide concise, constructive feedback.

Interview Question:
"{question}"

Expected Key Topics:
{topics_str}

Student's Answer:
"{student_answer}"

Instructions:
- Evaluate whether the student covers the expected key topics.
- Write 2-3 sentences of specific, constructive feedback.
- Do NOT output preamble, markdown headings, or filler text."""

    elif task_type == "gap_summary":
        rejected_apps = context.get("rejected_applications", [])
        if rejected_apps:
            lines = []
            for app in rejected_apps:
                if isinstance(app, dict):
                    role = app.get("role_tag", "General")
                    stage = app.get("rejection_stage", "Unknown")
                    lines.append(f"- Role: {role} | Stage: {stage}")
            apps_text = "\n".join(lines) if lines else "- No application data"
        else:
            apps_text = "- No application data"

        return f"""You are Placement Copilot's Gap Analysis Agent.
Analyze the following list of rejected or ghosted job applications to identify the single most prominent rejection pattern.

Application Outcomes:
{apps_text}

Instructions:
- Identify the main bottleneck stage (e.g., Online Assessment / OA) and role category.
- Summarize the pattern and actionable insight in 1-2 concise sentences.
- Do NOT output preamble, titles, or conversational filler."""

    return f"Summarize the following context concisely: {context}"


@router.post("/llm-generate", response_model=LLMGenerateResponse)
async def llm_generate(payload: LLMGenerateRequest) -> LLMGenerateResponse:
    """
    Generate LLM text response using local Ollama (llama3.1:8b).
    Handles scam_explanation, answer_feedback, and gap_summary tasks.
    Falls back gracefully to deterministic text if Ollama is offline or times out (10s limit).
    """
    prompt = _build_prompt(payload.task_type, payload.context)

    ollama_body = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.2,
            "num_predict": 250,
        },
    }

    try:
        async with httpx.AsyncClient(timeout=OLLAMA_TIMEOUT) as client:
            response = await client.post(OLLAMA_URL, json=ollama_body)
            response.raise_for_status()
            data = response.json()
            generated_text = data.get("response", "").strip()

            if generated_text:
                return LLMGenerateResponse(
                    generated_text=generated_text,
                    task_type=payload.task_type,
                )
            else:
                logger.warning(
                    f"Ollama returned empty response for task_type '{payload.task_type}'. Using fallback."
                )

    except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPStatusError, Exception) as err:
        logger.warning(
            f"Ollama local instance unavailable or timed out ({err}). "
            f"Falling back to deterministic response for task_type '{payload.task_type}'."
        )

    # Fallback path if Ollama is unreachable, times out, or errors out
    fallback_text = _generate_placeholder_text(payload.task_type, payload.context)
    return LLMGenerateResponse(
        generated_text=fallback_text,
        task_type=payload.task_type,
        error="llm_unavailable",
    )
