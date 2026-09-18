import os
import json
import re
from typing import Any, Dict, List
from sqlalchemy.orm import Session
from models import Application, TailoredResume


def _load_base_resume() -> List[Dict[str, Any]]:
    """Load base resume bullets from base_resume.json."""
    file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "base_resume.json")
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("base_bullets", [])
    # Fallback default base bullets if file is missing
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
    Deterministic Tailoring Agent (No LLM call, no model-service call).
    Reorders student's base resume bullets based on keyword overlap with JD text.
    Updates application status to READY_TO_APPLY and links tailored_resume_id.
    """
    base_bullets = _load_base_resume()
    jd_keywords = _extract_keywords(application.jd_text)

    scored_bullets = []
    for item in base_bullets:
        bullet_kw = {k.lower() for k in item.get("keywords", [])}
        overlap = bullet_kw.intersection(jd_keywords)
        if bullet_kw:
            score = len(overlap) / len(bullet_kw)
        else:
            score = 0.0

        # Also add text-level keyword matches
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

    resume_data = {
        "ordered_bullets": scored_bullets
    }

    # Save to tailored_resumes table
    tailored_record = TailoredResume(
        application_id=application.id,
        resume_data=resume_data,
        match_score=max_score,
    )
    db.add(tailored_record)
    db.commit()
    db.refresh(tailored_record)

    # Update application row: set status READY_TO_APPLY and link tailored_resume_id
    application.status = "READY_TO_APPLY"
    application.tailored_resume_id = tailored_record.id
    db.commit()
    db.refresh(application)

    return {
        "tailored_resume_id": tailored_record.id,
        "resume_data": resume_data,
    }
