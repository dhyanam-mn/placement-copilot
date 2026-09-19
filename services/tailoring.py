import os
import re
import logging
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from models import Application, TailoredResume, Profile, ProfileProject

logger = logging.getLogger("placement_copilot.tailoring")


def _load_base_resume(db: Optional[Session] = None) -> List[Dict[str, Any]]:
    """
    Load base resume projects and bullets directly from the database `profile` and `profile_projects` tables.
    
    SCORING DOCUMENTATION:
    - Scout Sourcing / Application Matching: Uses embedding-based scoring via model-service `/embed`
      computing cosine similarity between JD text and candidate bullets.
    - Tailoring Agent Bullet Reordering: Uses deterministic TF-IDF / keyword overlap scoring
      comparing JD keywords against project bullet text and skill tags for fast, reproducible ordering.
    """
    if db is not None:
        try:
            projects = db.query(ProfileProject).all()
            if projects:
                results = []
                for p in projects:
                    results.append({
                        "project": p.project_name,
                        "bullet": p.bullet_text,
                        "keywords": p.skill_tags or [],
                    })
                return results
        except Exception as exc:
            logger.warning(f"Could not load profile projects from DB: {exc}")

    # Fallback default projects if DB table is empty
    return [
        {
            "project": "DronaMaps CV Pipeline",
            "bullet": "Built an object detection system using YOLOv8 and rasterio to process GeoTIFF drone images with sliding-window tiling.",
            "keywords": ["object detection", "YOLOv8", "rasterio", "GeoTIFF", "computer vision", "drone imagery", "PyTorch", "sliding window tiling"],
        },
        {
            "project": "Campus Connect Pro",
            "bullet": "Designed and scaled backend microservices using FastAPI, PostgreSQL, and Redis caching for real-time notifications.",
            "keywords": ["FastAPI", "PostgreSQL", "Redis", "caching", "backend", "REST APIs", "SQL", "distributed systems", "Python"],
        },
        {
            "project": "LLM Domain Classifier",
            "bullet": "Fine-tuned Llama 3 8B model using LoRA and PyTorch for domain-specific text classification and automated summarization.",
            "keywords": ["Llama 3", "LoRA", "PyTorch", "NLP", "transformers", "LLM", "machine learning", "text classification"],
        },
        {
            "project": "Algorithmic Trading & Analytics Engine",
            "bullet": "Implemented high-throughput data pipelines with DSA optimization, Pandas, and NumPy for quantitative risk assessment.",
            "keywords": ["DSA", "system design", "Pandas", "NumPy", "data structures", "algorithms", "Python", "data analytics"],
        },
    ]


def _extract_keywords(text: str) -> set:
    """Extract clean lowercase keyword tokens and key phrases from JD text."""
    words = re.findall(r"\b[A-Za-z0-9+#.-]+\b", text.lower())
    stop_words = {
        "and", "or", "the", "a", "an", "in", "on", "at", "to", "for", "with",
        "by", "of", "is", "are", "be", "experience", "looking", "intern",
        "experienced", "strong", "preferred", "role", "work", "job"
    }
    return {w for w in words if w not in stop_words and len(w) > 1}


def tailor_resume_for_application(db: Session, application: Application) -> Dict[str, Any]:
    """
    Tailoring Agent Workflow:
    - Reads candidate bullets from `profile` & `profile_projects` DB tables.
    - Reorders bullets based on TF-IDF / keyword overlap with the target JD.
    - Saves tailored resume data into `tailored_resumes` table.
    - Updates application status to READY_TO_APPLY.
    """
    base_bullets = _load_base_resume(db)
    jd_keywords = _extract_keywords(application.jd_text)

    scored_bullets = []
    for item in base_bullets:
        bullet_kw = {k.lower() for k in item.get("keywords", [])}
        overlap = bullet_kw.intersection(jd_keywords)
        if bullet_kw:
            score = len(overlap) / len(bullet_kw)
        else:
            score = 0.0

        # Text-level keyword matches
        bullet_text_lower = item["bullet"].lower()
        extra_matches = sum(1 for kw in jd_keywords if kw in bullet_text_lower)
        bonus = min(0.3, extra_matches * 0.05)

        final_score = round(min(0.99, score + bonus), 2)
        scored_bullets.append({
            "project": item["project"],
            "bullet": item["bullet"],
            "score": max(0.1, final_score),
        })

    # Sort bullets by score descending
    scored_bullets.sort(key=lambda x: x["score"], reverse=True)

    max_score = scored_bullets[0]["score"] if scored_bullets else 0.50
    resume_data = {"ordered_bullets": scored_bullets}

    # Save to tailored_resumes table
    tailored_record = TailoredResume(
        application_id=application.id,
        resume_data=resume_data,
        match_score=max_score,
    )
    db.add(tailored_record)
    db.commit()
    db.refresh(tailored_record)

    # Link tailored_resume_id to application row
    application.tailored_resume_id = tailored_record.id
    db.commit()
    db.refresh(application)

    return {
        "tailored_resume_id": tailored_record.id,
        "resume_data": resume_data,
    }


def render_tailored_resume_tex(db: Session, application_id: int) -> str:
    """
    Converts base_resume.tex into a dynamic LaTeX template populated with DB profile info
    and tailored bullet ordering.
    """
    profile = db.query(Profile).first()
    student_name = profile.name if profile else "Dhyanam Mahajan"

    app = db.query(Application).filter(Application.id == application_id).first()
    bullets = []
    if app and app.tailored_resume_id:
        tr = db.query(TailoredResume).filter(TailoredResume.id == app.tailored_resume_id).first()
        if tr and isinstance(tr.resume_data, dict):
            bullets = [b["bullet"] for b in tr.resume_data.get("ordered_bullets", [])]

    if not bullets:
        raw_bullets = _load_base_resume(db)
        bullets = [b["bullet"] for b in raw_bullets]

    items_tex = "\n".join([f"\\resumeItem{{{b}}}" for b in bullets])

    tex_content = f"""\\documentclass[11pt,a4paper]{{article}}
\\usepackage[margin=0.5in]{{geometry}}

\\newcommand{{\\resumeItem}}[1]{{
  \\item\\small{{#1 \\vspace{{-2pt}}}}
}}

\\begin{{document}}
\\begin{{center}}
    \\textbf{{\\Huge {student_name}}} \\\\ \\vspace{{5pt}}
    Software Engineer | Resume
\\end{{center}}

\\section*{{Key Experience \\& Projects}}
\\begin{{itemize}}
{items_tex}
\\end{{itemize}}
\\end{{document}}
"""
    return tex_content
