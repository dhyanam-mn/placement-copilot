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

    elif task_type == "prep_recommendations":
        jd_summary = context.get("jd_summary", "")
        candidates = context.get("candidates", [])

        candidates_lines = []
        for c in candidates:
            if isinstance(c, dict):
                c_id = c.get("id")
                c_title = c.get("title", "")
                c_skills = ", ".join(c.get("skills", []))
                candidates_lines.append(f"- ID: {c_id}, Title: {c_title}, Skills: {c_skills}")

        candidates_text = "\n".join(candidates_lines) if candidates_lines else "- No candidate resources provided"

        return f"""You are Placement Copilot's Prep Agent.
Given a Job Description summary and candidate learning resources, recommend up to 10 relevant resources to bridge technical skill gaps.

Job Description Summary:
{jd_summary}

Candidate Learning Resources:
{candidates_text}

Instructions:
- Output STRICT JSON only: a JSON array of objects.
- Each object must have fields: "resource_id" (integer), "reason" (string, concise rationale), and "est_hours" (integer).
- Do NOT output preamble, markdown formatting, code fences, or extra text."""

    elif task_type == "gap_summary":
        if "jd_required_skills" in context or "missing_skills" in context:
            company = context.get("company", "the company")
            role = context.get("role", "the role")
            required = context.get("jd_required_skills", [])
            matched = context.get("matched_skills", [])
            missing = context.get("missing_skills", [])
            
            req_str = ", ".join(required) if required else "None"
            matched_str = ", ".join(matched) if matched else "None"
            missing_str = ", ".join(missing) if missing else "None"
            
            if not missing:
                missing_note = "All primary JD technical skills were matched in the resume. No missing technical skill gap was identified for this application."
            else:
                missing_note = f"Missing required technical skills: {missing_str}."

            return f"""You are Placement Copilot's Gap Analysis Agent.
Write a clear 1-2 sentence per-row gap summary for a specific job application.

Application Context:
- Company: {company}
- Role: {role}
- Required Skills: {req_str}
- Matched Skills: {matched_str}
- Missing Skills: {missing_str}

Key Finding: {missing_note}

Instructions:
- Write 1-2 concise sentences summarizing the technical skill gap for THIS specific application.
- If no skills are missing, state that the candidate met all primary technical requirements and the rejection/ghosting occurred post-assessment.
- Do NOT mention aggregate patterns or other applications.
- Do NOT output preamble, markdown headings, or conversational filler."""

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
- Identify the main bottleneck stage (e.g., Online Assessment / OA) and role category across all applications.
- Summarize the pattern and actionable insight in 1-2 concise sentences.
- Do NOT output preamble, titles, or conversational filler."""

    return f"Summarize the following context concisely: {context}"


@router.post(
    "/llm-generate",
    response_model=LLMGenerateResponse,
    response_model_exclude_none=True,
)
async def llm_generate(payload: LLMGenerateRequest) -> LLMGenerateResponse:
    """
    Generate LLM text response using local Ollama (llama3.1:8b).
    Handles scam_explanation, prep_recommendations, and gap_summary tasks.
    Falls back gracefully to error='llm_unavailable' if Ollama is offline or times out (10s limit).
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
                    f"Ollama returned empty response for task_type '{payload.task_type}'."
                )

    except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPStatusError, Exception) as err:
        logger.warning(
            f"Ollama local instance unavailable or timed out ({err}). "
            f"Returning error='llm_unavailable' for task_type '{payload.task_type}'."
        )

    # Fallback path if Ollama is unreachable, times out, or errors out
    return LLMGenerateResponse(
        generated_text="",
        task_type=payload.task_type,
        error="llm_unavailable",
    )
