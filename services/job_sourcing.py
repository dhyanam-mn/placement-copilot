import os
import json
import html
import re
import logging
from typing import Any, Dict, List, Optional
import httpx
import numpy as np
from sqlalchemy import func
from sqlalchemy.orm import Session

from models import Application, CompanyWatchlist, ScamCheck, Setting
from schemas import ApplicationCreateRequest
from services.model_service_client import call_embed, call_llm_generate, ModelServiceUnavailableError
from services.tailoring import _load_base_resume
from scam_check import check_scam

logger = logging.getLogger("placement_copilot.job_sourcing")

UNSTOP_API_KEY = os.getenv("UNSTOP_API_KEY", "")
ADZUNA_APP_ID = os.getenv("ADZUNA_APP_ID", "")
ADZUNA_APP_KEY = os.getenv("ADZUNA_APP_KEY", "")


def _cosine_sim(v1: list, v2: list) -> float:
    a = np.array(v1, dtype=float)
    b = np.array(v2, dtype=float)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


def _clean_text(text: str) -> str:
    if not text:
        return ""
    # Unescape HTML entities
    cleaned = html.unescape(text)
    # Strip HTML tags
    cleaned = re.sub(r'<[^>]+>', ' ', cleaned)
    # Collapse multiple whitespaces
    return re.sub(r'\s+', ' ', cleaned).strip()


def load_companies_watchlist(db: Optional[Session] = None) -> List[Dict[str, str]]:
    """Load company watchlist strictly from company_watchlist DB table."""
    targets = []
    close_db = False
    if db is None:
        try:
            from database import SessionLocal
            db = SessionLocal()
            close_db = True
        except Exception:
            db = None

    if db is not None:
        try:
            db_watchlist = db.query(CompanyWatchlist).filter(CompanyWatchlist.active == True).all()
            for wl in db_watchlist:
                targets.append({"company": wl.company, "ats": wl.ats, "token": wl.token})
        except Exception as exc:
            logger.warning(f"Could not load watchlist from DB: {exc}")
        finally:
            if close_db:
                db.close()

    return targets


# ==============================================================================
# 1. Adzuna India Fetcher
# ==============================================================================

async def fetch_adzuna_jobs(query: str = "Software Engineer", location: str = "India") -> List[Dict[str, Any]]:
    if not ADZUNA_APP_ID or not ADZUNA_APP_KEY:
        logger.warning("ADZUNA keys not configured in environment. Skipping Adzuna live fetch.")
        return []

    url = "https://api.adzuna.com/v1/api/jobs/in/search/1"
    params = {
        "app_id": ADZUNA_APP_ID,
        "app_key": ADZUNA_APP_KEY,
        "results_per_page": 20,
        "what": query,
        "content-type": "application/json"
    }

    jobs = []
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, params=params)
            if resp.status_code != 200:
                logger.error(f"Adzuna returned status code {resp.status_code}: {resp.text}")
                return []
            data = resp.json()
            results = data.get("results", [])
            for item in results:
                company = _clean_text((item.get("company", {}) or {}).get("display_name", ""))
                title = _clean_text(item.get("title", ""))
                description = _clean_text(item.get("description", "")) or f"Role at {company}: {title}"
                if company and title:
                    jobs.append({
                        "company": company,
                        "role": title,
                        "jd_text": description,
                        "source": "adzuna",
                    })
    except Exception as exc:
        logger.error(f"Error fetching from Adzuna: {exc}")

    return jobs


# ==============================================================================
# 2. ATS Fetchers (Greenhouse, Lever)
# ==============================================================================

async def fetch_greenhouse_jobs(token: str, company_name: str) -> List[Dict[str, Any]]:
    url = f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true"
    jobs = []
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                data = resp.json()
                for job in data.get("jobs", []):
                    title = _clean_text(job.get("title", ""))
                    content_raw = job.get("content", "") or ""
                    jd_text = _clean_text(content_raw) or f"Job role {title} at {company_name}"
                    if title:
                        jobs.append({
                            "company": company_name,
                            "role": title,
                            "jd_text": jd_text,
                            "source": "greenhouse",
                        })
    except Exception as exc:
        logger.error(f"Error fetching Greenhouse for {company_name}: {exc}")
    return jobs


async def fetch_lever_jobs(token: str, company_name: str) -> List[Dict[str, Any]]:
    url = f"https://api.lever.co/v0/postings/{token}?mode=json"
    jobs = []
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list):
                    for job in data:
                        title = _clean_text(job.get("text", ""))
                        jd_plain = job.get("descriptionPlain", "") or ""
                        if not jd_plain:
                            content_obj = job.get("content", {}) or {}
                            jd_plain = content_obj.get("description", "") or ""
                        jd_text = _clean_text(jd_plain) or f"Job role {title} at {company_name}"
                        if title:
                            jobs.append({
                                "company": company_name,
                                "role": title,
                                "jd_text": jd_text,
                                "source": "lever",
                            })
    except Exception as exc:
        logger.error(f"Error fetching Lever for {company_name}: {exc}")
    return jobs


async def fetch_ats_jobs(db: Optional[Session] = None) -> List[Dict[str, Any]]:
    targets = load_companies_watchlist(db)

    # Deduplicate targets by (ats, token)
    seen = set()
    unique_targets = []
    for t in targets:
        ats = (t.get("ats") or "").lower().strip()
        token = (t.get("token") or "").strip()
        company = (t.get("company") or "").strip()
        key = (ats, token.lower())
        if ats and token and key not in seen:
            seen.add(key)
            unique_targets.append({"company": company, "ats": ats, "token": token})

    jobs = []
    for target in unique_targets:
        ats = target["ats"]
        token = target["token"]
        company = target["company"]
        if ats == "greenhouse":
            jobs.extend(await fetch_greenhouse_jobs(token, company))
        elif ats == "lever":
            jobs.extend(await fetch_lever_jobs(token, company))
    return jobs


# ==============================================================================
# 3. Unstop Job Listings Fetcher
# ==============================================================================

async def fetch_unstop_jobs(query: str = "Developer") -> List[Dict[str, Any]]:
    url = "https://unstop.com/api/public/opportunity/search-result"
    headers = {"User-Agent": "Placement-Copilot/1.0"}
    if UNSTOP_API_KEY:
        headers["Authorization"] = f"Bearer {UNSTOP_API_KEY}"

    params = {
        "opportunity": "jobs",
        "searchTerm": query,
        "per_page": 10,
    }

    jobs = []
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, params=params, headers=headers)
            if resp.status_code != 200:
                logger.warning(f"Unstop API returned status code {resp.status_code}")
                return []
            data = resp.json()
            data_items = data.get("data", {}).get("data", []) or data.get("data", [])
            if isinstance(data_items, list):
                for item in data_items:
                    company = (item.get("organisation", {}) or {}).get("name") or item.get("company_name") or item.get("company", "")
                    title = item.get("title") or item.get("role", "")
                    description = item.get("details") or item.get("about") or item.get("job_description") or f"Job listing at {company}"

                    company_clean = _clean_text(str(company)) if company else ""
                    title_clean = _clean_text(str(title)) if title else ""
                    desc_clean = _clean_text(str(description)) if description else f"Role: {title_clean}"

                    if company_clean and title_clean:
                        jobs.append({
                            "company": company_clean,
                            "role": title_clean,
                            "jd_text": desc_clean,
                            "source": "unstop",
                        })
    except Exception as exc:
        logger.error(f"Error fetching from Unstop API: {exc}")

    return jobs


# ==============================================================================
# 4. Deduplication Helper
# ==============================================================================

def is_duplicate_application(db: Session, company: str, role: str, source: str) -> bool:
    existing = (
        db.query(Application)
        .filter(
            func.lower(Application.company) == company.lower().strip(),
            func.lower(Application.role) == role.lower().strip(),
            Application.source == source,
        )
        .first()
    )
    return existing is not None


# ==============================================================================
# 5. Main Sourcing Runner
# ==============================================================================

async def run_job_sourcing(
    db: Session,
    dry_run: bool = False,
    query: str = "Software Engineer",
    mock_listings: Optional[List[Dict[str, Any]]] = None,
    high_risk_action: Optional[str] = None,
) -> Dict[str, Any]:
    # Determine high risk action setting if not provided (defaulting to 'skip')
    if not high_risk_action:
        try:
            setting = db.query(Setting).filter(Setting.key == "scout_high_risk_action").first()
            if setting and isinstance(setting.value, dict):
                high_risk_action = setting.value.get("action", "skip")
            elif setting and isinstance(setting.value, str):
                high_risk_action = setting.value
            else:
                high_risk_action = "skip"
        except Exception:
            high_risk_action = "skip"

    all_listings: List[Dict[str, Any]] = []

    if mock_listings is not None:
        all_listings = mock_listings
    else:
        # Live fetch from sources
        adzuna_jobs = await fetch_adzuna_jobs(query=query)
        ats_jobs = await fetch_ats_jobs(db)
        unstop_jobs = await fetch_unstop_jobs(query=query)
        all_listings = adzuna_jobs + ats_jobs + unstop_jobs

    processed_results = []
    skipped_duplicates = 0
    seen_in_batch = set()

    base_bullets = _load_base_resume(db)
    sample_bullets = [b["bullet"] for b in base_bullets]

    for item in all_listings:
        company = item.get("company", "").strip()
        role = item.get("role", "").strip()
        jd_text = item.get("jd_text", "").strip()
        source = item.get("source", "adzuna").lower().strip()

        if not company or not role or not jd_text:
            continue

        if source not in ("adzuna", "greenhouse", "lever", "unstop"):
            source = "adzuna"

        # In-batch deduplication
        batch_key = (company.lower(), role.lower(), source)
        if batch_key in seen_in_batch:
            skipped_duplicates += 1
            continue
        seen_in_batch.add(batch_key)

        # Database deduplication
        if is_duplicate_application(db, company, role, source):
            logger.info(f"Skipping duplicate listing: '{company}' - '{role}' ({source})")
            skipped_duplicates += 1
            continue

        # Embed Scoring via model-service
        texts = [jd_text] + sample_bullets
        try:
            embed_resp = await call_embed(texts)
            embeddings = embed_resp.get("embeddings", [])
            if len(embeddings) >= 2:
                jd_emb = embeddings[0]
                bullet_embs = embeddings[1:]
                scores = [_cosine_sim(jd_emb, b_emb) for b_emb in bullet_embs]
                match_score = round(float(max(scores)), 2)
            else:
                match_score = 0.50
        except Exception:
            match_score = 0.50

        # Pre-insert Scam-Check rule engine on recruiter domain & JD text
        recruiter_domain = item.get("recruiter_domain") or f"{company.lower().replace(' ', '').replace('-', '')}.com"
        recruiter_name = item.get("recruiter_name") or f"Scout ({source})"
        sender_email = f"recruiter@{recruiter_domain}"

        scam_res = check_scam(
            sender_email=sender_email,
            claimed_company=company,
            message_text=jd_text
        )

        risk_score = scam_res.get("risk_score", 0.0)
        flagged_reasons = scam_res.get("flagged_reasons", [])

        # Lower prior risk for direct ATS boards (Greenhouse/Lever)
        if source in ("greenhouse", "lever"):
            risk_score = max(0.0, round(risk_score - 0.2, 2))

        from services.settings_service import get_scam_threshold
        scam_thresh = get_scam_threshold(db)
        is_high_risk = risk_score >= scam_thresh

        if is_high_risk:
            if high_risk_action == "skip":
                logger.warning(f"Skipping high-risk scam job '{role}' at '{company}' (Risk: {risk_score})")
                if not dry_run:
                    # Store evidence in scam_checks with application_id = None
                    scam_record = ScamCheck(
                        application_id=None,
                        recruiter_name=recruiter_name,
                        recruiter_domain=recruiter_domain,
                        risk_score=risk_score,
                        flagged_reasons=flagged_reasons,
                        explanation_text=None,
                    )
                    db.add(scam_record)
                    db.commit()

                    if flagged_reasons:
                        import asyncio
                        from scam_check import generate_scam_explanation_background
                        asyncio.create_task(generate_scam_explanation_background(scam_record.id))

                processed_results.append({
                    "action": "skipped_high_risk_scam",
                    "company": company,
                    "role": role,
                    "source": source,
                    "risk_score": risk_score,
                    "flagged_reasons": flagged_reasons,
                })
                continue
            else: # "flag" action
                if dry_run:
                    processed_results.append({
                        "action": "would_insert_flagged",
                        "company": company,
                        "role": role,
                        "source": source,
                        "match_score": match_score,
                        "risk_score": risk_score,
                        "jd_text_snippet": jd_text[:100] + "...",
                    })
                else:
                    from routers.applications import process_and_create_application
                    req_payload = ApplicationCreateRequest(
                        company=company,
                        role=role,
                        jd_text=jd_text,
                        source=source,
                    )
                    created_app = await process_and_create_application(req_payload, db)

                    scam_record = ScamCheck(
                        application_id=created_app.id,
                        recruiter_name=recruiter_name,
                        recruiter_domain=recruiter_domain,
                        risk_score=risk_score,
                        flagged_reasons=flagged_reasons,
                        explanation_text=None,
                    )
                    db.add(scam_record)
                    db.commit()

                    if flagged_reasons:
                        import asyncio
                        from scam_check import generate_scam_explanation_background
                        asyncio.create_task(generate_scam_explanation_background(scam_record.id))

                    processed_results.append({
                        "action": "inserted_flagged",
                        "id": created_app.id,
                        "company": created_app.company,
                        "role": created_app.role,
                        "source": created_app.source,
                        "match_score": created_app.match_score,
                        "status": created_app.status,
                        "risk_score": risk_score,
                    })
        else:
            # Low/Medium Risk
            if dry_run:
                processed_results.append({
                    "action": "would_insert",
                    "company": company,
                    "role": role,
                    "source": source,
                    "match_score": match_score,
                    "jd_text_snippet": jd_text[:100] + "...",
                })
            else:
                from routers.applications import process_and_create_application
                req_payload = ApplicationCreateRequest(
                    company=company,
                    role=role,
                    jd_text=jd_text,
                    source=source,
                )
                created_app = await process_and_create_application(req_payload, db)

                # Record scam check evidence if risk > 0
                if risk_score > 0:
                    scam_record = ScamCheck(
                        application_id=created_app.id,
                        recruiter_name=recruiter_name,
                        recruiter_domain=recruiter_domain,
                        risk_score=risk_score,
                        flagged_reasons=flagged_reasons,
                        explanation_text=None,
                    )
                    db.add(scam_record)
                    db.commit()

                processed_results.append({
                    "action": "inserted",
                    "id": created_app.id,
                    "company": created_app.company,
                    "role": created_app.role,
                    "source": created_app.source,
                    "match_score": created_app.match_score,
                    "status": created_app.status,
                })

    return {
        "status": "success",
        "dry_run": dry_run,
        "total_fetched": len(all_listings),
        "duplicates_skipped": skipped_duplicates,
        "processed_count": len(processed_results),
        "results": processed_results,
    }
