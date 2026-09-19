import os
import re
import json
import hashlib
import logging
from typing import Dict, List, Set, Any, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from models import (
    Application,
    Skill,
    Resource,
    ResourceSkill,
    PrepRecommendation,
    LLMCache,
    ProfileProject,
)
from services.model_service_client import call_llm_generate, ModelServiceUnavailableError
from services.tailoring import _load_base_resume

logger = logging.getLogger("placement_copilot.prep_agent")


def _stem(word: str) -> str:
    """Lightweight suffix strip for common English verb/plural forms."""
    w = word.lower().strip()
    for suffix in ("ing", "ed", "es", "s"):
        if w.endswith(suffix) and len(w) > len(suffix) + 2:
            return w[:-len(suffix)]
    return w


def extract_jd_skills(db: Session, jd_text: str) -> List[str]:
    """
    Extract skills from job description deterministically using skills table
    (name + aliases, whole-word matching, light stemming).
    """
    if not jd_text:
        return []

    jd_text_lower = jd_text.lower()
    skills = db.query(Skill).all()
    matched_skills = set()

    for skill in skills:
        patterns = [skill.name.lower()]
        if skill.aliases and isinstance(skill.aliases, list):
            for alias in skill.aliases:
                if isinstance(alias, str) and alias.strip():
                    patterns.append(alias.lower().strip())

        for pattern in patterns:
            # Whole-word regex match
            escaped = re.escape(pattern)
            regex = r'\b' + escaped + r'\b'
            if re.search(regex, jd_text_lower):
                matched_skills.add(skill.name)
                break
            else:
                # Stemming fallback check
                stemmed_pattern = _stem(pattern)
                if len(stemmed_pattern) >= 3:
                    stem_regex = r'\b' + re.escape(stemmed_pattern) + r'\w*\b'
                    if re.search(stem_regex, jd_text_lower):
                        matched_skills.add(skill.name)
                        break

    return sorted(list(matched_skills))


def get_profile_skills(db: Session) -> Set[str]:
    """Retrieve profile skills from profile projects and base resume bullets."""
    profile_skills = set()
    try:
        projects = db.query(ProfileProject).all()
        for p in projects:
            if p.skill_tags and isinstance(p.skill_tags, list):
                for tag in p.skill_tags:
                    if isinstance(tag, str):
                        profile_skills.add(tag.strip())
            if p.bullet_text:
                for word in p.bullet_text.split():
                    profile_skills.add(word.strip().strip(",.").lower())
    except Exception as exc:
        logger.warning(f"Could not load profile projects for skills: {exc}")

    try:
        base_bullets = _load_base_resume()
        for b in base_bullets:
            bullet_str = b.get("bullet", "") if isinstance(b, dict) else str(b)
            for word in bullet_str.split():
                profile_skills.add(word.strip().strip(",.").lower())
    except Exception:
        pass

    return profile_skills


def rank_resources_sql(
    db: Session, jd_skills: List[str], gap_skills: Set[str], profile_skills: Set[str], limit: int = 10
) -> List[Dict[str, Any]]:
    """
    SQL-rank active resources via resource_skills, weighting gap skills higher (2.5x).
    Returns top candidates: [{ 'id': res_id, 'title': res_title, 'skills': [matched_skills] }].
    """
    active_resources = db.query(Resource).filter(Resource.is_active == True).all()
    if not active_resources:
        # Fallback to all resources if none active
        active_resources = db.query(Resource).all()

    resource_scores = {}
    resource_matched_skills = {}

    for res in active_resources:
        score = 0.0
        matched = []
        for rs in res.skills:
            s_name = rs.skill_name
            if s_name in jd_skills or any(s_name.lower() in j.lower() for j in jd_skills):
                w = rs.weight or 1.0
                if s_name in gap_skills or any(s_name.lower() in g.lower() for g in gap_skills):
                    score += w * 2.5
                else:
                    score += w * 1.0
                matched.append(s_name)

        if score > 0 or not jd_skills:
            resource_scores[res.id] = score
            resource_matched_skills[res.id] = matched

    # Sort descending by score
    sorted_res_ids = sorted(resource_scores.keys(), key=lambda r_id: resource_scores[r_id], reverse=True)
    top_ids = sorted_res_ids[:limit]

    candidates = []
    res_map = {res.id: res for res in active_resources}
    for r_id in top_ids:
        res_obj = res_map.get(r_id)
        if res_obj:
            candidates.append({
                "id": res_obj.id,
                "title": res_obj.title,
                "skills": resource_matched_skills.get(r_id, []),
            })

    return candidates


def _get_cached_llm_response(db: Session, prompt_hash: str) -> Optional[str]:
    try:
        cached = db.query(LLMCache).filter(LLMCache.prompt_hash == prompt_hash).first()
        if cached:
            return cached.response
    except Exception as exc:
        logger.warning(f"Error querying llm_cache: {exc}")
    return None


def _save_llm_cache(db: Session, prompt_hash: str, response_text: str) -> None:
    try:
        existing = db.query(LLMCache).filter(LLMCache.prompt_hash == prompt_hash).first()
        if not existing:
            cached_record = LLMCache(prompt_hash=prompt_hash, response=response_text)
            db.add(cached_record)
            db.commit()
    except Exception as exc:
        logger.warning(f"Error saving to llm_cache: {exc}")
        db.rollback()


async def _background_ollama_fetch_and_cache(prompt_hash: str, context_payload: Dict[str, Any]) -> None:
    """Background task to complete slow Ollama call and store result in llm_cache."""
    from database import SessionLocal
    db = SessionLocal()
    try:
        llm_resp = await call_llm_generate("prep_recommendations", context=context_payload)
        gen_text = llm_resp.get("generated_text", "")
        if gen_text:
            _save_llm_cache(db, prompt_hash, gen_text)
            logger.info(f"Background Ollama fetch completed and saved to llm_cache (hash: {prompt_hash[:8]}).")
    except Exception as exc:
        logger.warning(f"Background Ollama fetch failed: {exc}")
    finally:
        db.close()


async def call_ollama_prep_recommendations(
    db: Session, jd_summary: str, candidate_resources: List[Dict[str, Any]]
) -> str:
    """
    Call Ollama for Prep Agent recommendations:
    - Checks llm_cache first.
    - Uses 5s timeout on model-service call.
    - If timeout occurs, triggers background task to populate llm_cache for next time and returns "" for fast deterministic fallback.
    """
    context_payload = {
        "jd_summary": jd_summary[:300],
        "candidates": candidate_resources,
    }

    # Hash prompt payload for llm_cache lookup
    prompt_str = json.dumps(context_payload, sort_keys=True)
    prompt_hash = hashlib.sha256(prompt_str.encode("utf-8")).hexdigest()

    cached_resp = _get_cached_llm_response(db, prompt_hash)
    if cached_resp:
        logger.info("Found cached LLM response in llm_cache.")
        return cached_resp

    try:
        import asyncio
        llm_resp = await asyncio.wait_for(
            call_llm_generate("prep_recommendations", context=context_payload),
            timeout=5.0
        )
        gen_text = llm_resp.get("generated_text", "")
        if gen_text:
            _save_llm_cache(db, prompt_hash, gen_text)
        return gen_text
    except (asyncio.TimeoutError, Exception) as exc:
        logger.warning(f"Ollama call timed out/failed (>5s: {exc}). Spawning background task for llm_cache...")
        import asyncio
        asyncio.create_task(_background_ollama_fetch_and_cache(prompt_hash, context_payload))
        return ""


def validate_and_parse_llm_json(
    response_text: str, valid_candidate_ids: Set[int], max_items: int = 5
) -> List[Dict[str, Any]]:
    """
    Validate LLM JSON response:
    - Drop unknown IDs.
    - Validate fields.
    - Cap length at max_items.
    """
    if not response_text:
        return []

    # Clean code fences if present
    cleaned = response_text.strip()
    if "```json" in cleaned:
        cleaned = cleaned.split("```json")[1].split("```")[0].strip()
    elif "```" in cleaned:
        cleaned = cleaned.split("```")[1].split("```")[0].strip()

    parsed = None
    try:
        parsed = json.loads(cleaned)
    except Exception:
        # Regex search for JSON array if extra markdown text surrounds it
        match = re.search(r'\[\s*\{.*\}\s*\]', cleaned, re.DOTALL)
        if match:
            try:
                parsed = json.loads(match.group(0))
            except Exception:
                parsed = None

    if not isinstance(parsed, list):
        return []

    valid_results = []
    seen_ids = set()

    for item in parsed:
        if not isinstance(item, dict):
            continue
        r_id = item.get("resource_id")
        reason = item.get("reason")
        est_hours = item.get("est_hours")

        try:
            r_id = int(r_id)
        except (TypeError, ValueError):
            continue

        if r_id not in valid_candidate_ids or r_id in seen_ids:
            continue

        if not reason or not isinstance(reason, str):
            reason = "Recommended resource aligned with your technical interview requirements."

        try:
            est_hours = int(est_hours)
        except (TypeError, ValueError):
            est_hours = 3

        seen_ids.add(r_id)
        valid_results.append({
            "resource_id": r_id,
            "reason": reason.strip(),
            "est_hours": max(1, est_hours),
        })

        if len(valid_results) >= max_items:
            break

    return valid_results


async def generate_prep_recommendations(
    db: Session, application: Application
) -> List[Dict[str, Any]]:
    """
    Core Prep Agent workflow:
    1. Extract JD skills.
    2. Compute gap = JD skills - profile skills.
    3. SQL-rank top 10 resources.
    4. Call Ollama with candidates and require strict JSON.
    5. Validate: drop unknown IDs, cap length, retry once, else fall back to SQL ranking.
    6. Store in prep_recommendations (URLs fetched strictly by resource ID).
    7. Cache LLM output in llm_cache.
    """
    jd_skills = extract_jd_skills(db, application.jd_text)
    profile_skills = get_profile_skills(db)
    gap_skills = set(jd_skills) - profile_skills
    if not gap_skills:
        gap_skills = set(jd_skills)

    candidate_resources = rank_resources_sql(db, jd_skills, gap_skills, profile_skills, limit=10)
    valid_candidate_ids = {c["id"] for c in candidate_resources}

    valid_recs = []

    if candidate_resources:
        # Attempt 1: Call Ollama & Validate
        raw_llm_resp = await call_ollama_prep_recommendations(db, application.jd_text, candidate_resources)
        valid_recs = validate_and_parse_llm_json(raw_llm_resp, valid_candidate_ids)

        # Attempt 2: Retry once if validation failed or returned 0 valid items
        if not valid_recs and raw_llm_resp:
            logger.info("Prep Agent Attempt 1 JSON validation failed. Retrying LLM call once...")
            raw_llm_resp_retry = await call_ollama_prep_recommendations(db, application.jd_text, candidate_resources)
            valid_recs = validate_and_parse_llm_json(raw_llm_resp_retry, valid_candidate_ids)

    # Fallback to deterministic SQL ranking if LLM recommendations are empty
    if not valid_recs and candidate_resources:
        logger.info("Falling back to deterministic SQL-ranked resource recommendations.")
        for item in candidate_resources[:4]:
            skills_str = ", ".join(item["skills"]) if item["skills"] else "core concepts"
            valid_recs.append({
                "resource_id": item["id"],
                "reason": f"Recommended resource for mastering {skills_str} based on your job description requirements.",
                "est_hours": 3,
            })

    # Clear previous recommendations for this application
    db.query(PrepRecommendation).filter(PrepRecommendation.application_id == application.id).delete()
    db.commit()

    # Store in prep_recommendations table
    created_records = []
    for rec in valid_recs:
        record = PrepRecommendation(
            application_id=application.id,
            resource_id=rec["resource_id"],
            reason=rec["reason"],
            est_hours=rec["est_hours"],
        )
        db.add(record)
        created_records.append(record)

    db.commit()

    return get_application_prep_recommendations(db, application.id)


def get_application_prep_recommendations(db: Session, application_id: int) -> List[Dict[str, Any]]:
    """
    Fetch stored recommendations for an application, strictly resolving title & URL from resources table by ID.
    """
    recs = (
        db.query(PrepRecommendation)
        .filter(PrepRecommendation.application_id == application_id)
        .all()
    )

    results = []
    for rec in recs:
        res_obj = rec.resource or db.query(Resource).filter(Resource.id == rec.resource_id).first()
        if res_obj:
            results.append({
                "id": rec.id,
                "application_id": rec.application_id,
                "resource_id": rec.resource_id,
                "title": res_obj.title,
                "url": res_obj.url,
                "reason": rec.reason,
                "est_hours": rec.est_hours,
                "created_at": rec.created_at.isoformat() if rec.created_at else None,
            })

    return results
