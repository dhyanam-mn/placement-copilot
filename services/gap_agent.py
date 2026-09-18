import re
from typing import Any, Dict, List
from sqlalchemy.orm import Session
from models import Application, GapReport
from services.model_service_client import call_llm_generate, ModelServiceUnavailableError


KNOWN_SKILLS = [
    "DSA", "system design", "SQL", "Python", "FastAPI", "React", "Node.js",
    "MongoDB", "Redis", "YOLO", "GeoTIFF", "rasterio", "object detection",
    "cloud deployment", "edge inference", "distributed systems", "PyTorch", "LoRA"
]


def _extract_jd_skills(jd_text: str) -> List[str]:
    """Extract known technical skill keywords present in JD text."""
    jd_lower = jd_text.lower()
    found = []
    for skill in KNOWN_SKILLS:
        if skill.lower() in jd_lower:
            found.append(skill)
    if not found:
        # Fallback keyword extraction from JD
        words = re.findall(r"\b[A-Z][a-z0-9]+\b", jd_text)
        found = list(set(words[:3])) if words else ["DSA", "SQL"]
    return found


def _get_matched_skills(required_skills: List[str]) -> tuple:
    """Divide required skills into matched vs missing against student profile skills."""
    student_skills = {
        "dsa", "python", "fastapi", "postgresql", "redis", "yolo",
        "geotiff", "rasterio", "object detection", "pytorch", "lora",
        "react", "node.js", "mongodb", "sql"
    }
    matched = []
    missing = []
    for skill in required_skills:
        if skill.lower() in student_skills:
            matched.append(skill)
        else:
            missing.append(skill)
    return matched, missing


async def generate_per_row_gap_report(db: Session, application: Application) -> GapReport:
    """Generate per-row gap report for a GHOSTED or REJECTED application."""
    # Check if a per-row report already exists
    if application.gap_report_id:
        existing = db.query(GapReport).filter(GapReport.id == application.gap_report_id).first()
        if existing:
            return existing

    required_skills = _extract_jd_skills(application.jd_text)
    matched, missing = _get_matched_skills(required_skills)

    details = {
        "jd_required_skills": required_skills,
        "matched_skills": matched,
        "missing_skills": missing,
    }

    if missing:
        missing_str = ", ".join(missing)
        fallback_summary = f"JD required {missing_str} — not present in the matched resume skills for this application."
    else:
        fallback_summary = "Candidate met all primary technical skills, but application was rejected/ghosted after assessment."

    # Attempt to call model-service /llm-generate for task_type 'gap_summary'
    try:
        role_tag = "SDE" if "sde" in application.role.lower() else ("CV" if "cv" in application.role.lower() else "General")
        context = {
            "rejected_applications": [
                {"role_tag": role_tag, "rejection_stage": application.status}
            ]
        }
        llm_resp = await call_llm_generate("gap_summary", context=context)
        summary_text = llm_resp.get("generated_text") or fallback_summary
    except (ModelServiceUnavailableError, Exception):
        summary_text = fallback_summary

    gap_report = GapReport(
        application_id=application.id,
        report_type="per_row",
        summary_text=summary_text,
        details=details,
    )
    db.add(gap_report)
    db.commit()
    db.refresh(gap_report)

    # Link report ID on application row
    application.gap_report_id = gap_report.id
    db.commit()

    return gap_report


async def generate_aggregate_gap_report(db: Session) -> GapReport:
    """Generate aggregate gap report across all GHOSTED and REJECTED applications."""
    rejected_rows = (
        db.query(Application)
        .filter(Application.status.in_(["GHOSTED", "REJECTED"]))
        .all()
    )

    by_role_tag: Dict[str, Dict[str, int]] = {}
    llm_rejected_list = []

    for app in rejected_rows:
        role_tag = "SDE" if "sde" in app.role.lower() or "software" in app.role.lower() else ("CV" if "cv" in app.role.lower() or "vision" in app.role.lower() else "General")
        stage = app.status

        llm_rejected_list.append({"role_tag": role_tag, "rejection_stage": stage})

        if role_tag not in by_role_tag:
            by_role_tag[role_tag] = {"total": 0, "rejected_at_oa": 0, "rejected_at_interview": 0}

        by_role_tag[role_tag]["total"] += 1
        if stage in ("OA_INVITE", "OA"):
            by_role_tag[role_tag]["rejected_at_oa"] += 1
        elif stage == "INTERVIEW":
            by_role_tag[role_tag]["rejected_at_interview"] += 1

    details = {"by_role_tag": by_role_tag}
    fallback_summary = f"{len(rejected_rows)} applications ended in rejection or ghosting across SDE and CV tracks."

    try:
        if llm_rejected_list:
            llm_resp = await call_llm_generate("gap_summary", context={"rejected_applications": llm_rejected_list})
            summary_text = llm_resp.get("generated_text") or fallback_summary
        else:
            summary_text = "No rejected or ghosted applications found to summarize."
    except (ModelServiceUnavailableError, Exception):
        summary_text = fallback_summary

    gap_report = GapReport(
        application_id=None,
        report_type="aggregate",
        summary_text=summary_text,
        details=details,
    )
    db.add(gap_report)
    db.commit()
    db.refresh(gap_report)

    return gap_report
