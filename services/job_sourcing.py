import os
import logging
from typing import Any, Dict, List, Optional
import httpx
from sqlalchemy import func
from sqlalchemy.orm import Session

from models import Application
from schemas import ApplicationCreateRequest
from services.model_service_client import call_embed
from services.tailoring import _load_base_resume
import numpy as np

logger = logging.getLogger("placement_copilot.job_sourcing")

SERPAPI_KEY = os.getenv("SERPAPI_KEY", "")
UNSTOP_API_KEY = os.getenv("UNSTOP_API_KEY", "")


def _cosine_sim(v1: list, v2: list) -> float:
    a = np.array(v1, dtype=float)
    b = np.array(v2, dtype=float)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


# ==============================================================================
# 1. SerpAPI (Google Jobs Engine) Fetcher
# ==============================================================================

async def fetch_serpapi_jobs(query: str = "Software Engineer", location: str = "India") -> List[Dict[str, Any]]:
    """
    Fetch job listings from SerpAPI's Google Jobs engine.
    Uses SERPAPI_KEY environment variable.
    """
    if not SERPAPI_KEY:
        logger.warning("SERPAPI_KEY not configured in environment. Skipping SerpAPI live fetch.")
        return []

    url = "https://serpapi.com/search.json"
    params = {
        "engine": "google_jobs",
        "q": query,
        "location": location,
        "api_key": SERPAPI_KEY,
    }

    jobs = []
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, params=params)
            if resp.status_code != 200:
                logger.error(f"SerpAPI returned status code {resp.status_code}: {resp.text}")
                return []
            data = resp.json()
            results = data.get("jobs_results", [])
            for item in results:
                company = item.get("company_name", "").strip()
                title = item.get("title", "").strip()
                description = item.get("description", "").strip() or f"Role at {company}: {title}"
                if company and title:
                    jobs.append({
                        "company": company,
                        "role": title,
                        "jd_text": description,
                        "source": "serpapi",
                    })
    except Exception as exc:
        logger.error(f"Error fetching from SerpAPI: {exc}")

    return jobs


# ==============================================================================
# 2. Unstop Job Listings Fetcher
# ==============================================================================

async def fetch_unstop_jobs(query: str = "Developer") -> List[Dict[str, Any]]:
    """
    Fetch job listings from Unstop's public opportunity search API.
    Optionally reads UNSTOP_API_KEY from environment variables if set.
    """
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

                    if isinstance(company, str) and isinstance(title, str) and company.strip() and title.strip():
                        jobs.append({
                            "company": company.strip(),
                            "role": title.strip(),
                            "jd_text": description.strip() if isinstance(description, str) else f"Role: {title}",
                            "source": "unstop",
                        })
    except Exception as exc:
        logger.error(f"Error fetching from Unstop API: {exc}")

    return jobs


# ==============================================================================
# 3. Deduplication Helper
# ==============================================================================

def is_duplicate_application(db: Session, company: str, role: str, source: str) -> bool:
    """
    Deduplicates against existing database rows matching on (company, role, source) case-insensitively.
    """
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
# 4. Main Sourcing Runner (with Dry-Run Mode Support)
# ==============================================================================

async def run_job_sourcing(
    db: Session,
    dry_run: bool = False,
    query: str = "Software Engineer",
    mock_listings: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Polls SerpAPI and Unstop for live job listings, deduplicates against DB,
    and feeds new unique listings into the embed-and-match application creation flow.

    If dry_run=True, fetches, deduplicates, and computes match scores without inserting rows.
    """
    all_listings: List[Dict[str, Any]] = []

    if mock_listings is not None:
        all_listings = mock_listings
    else:
        # Live fetch from both sources
        serp_jobs = await fetch_serpapi_jobs(query=query)
        unstop_jobs = await fetch_unstop_jobs(query=query)
        all_listings = serp_jobs + unstop_jobs

    processed_results = []
    skipped_duplicates = 0

    base_bullets = _load_base_resume()
    sample_bullets = [b["bullet"] for b in base_bullets]

    for item in all_listings:
        company = item.get("company", "").strip()
        role = item.get("role", "").strip()
        jd_text = item.get("jd_text", "").strip()
        source = item.get("source", "serpapi")

        if not company or not role or not jd_text:
            continue

        # Enforce source constraint
        if source not in ("serpapi", "unstop"):
            source = "serpapi"

        # Check deduplication
        if is_duplicate_application(db, company, role, source):
            logger.info(f"Skipping duplicate listing: '{company}' - '{role}' ({source})")
            skipped_duplicates += 1
            continue

        if dry_run:
            # Preview / Dry-run calculation
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

            processed_results.append({
                "action": "would_insert",
                "company": company,
                "role": role,
                "source": source,
                "match_score": match_score,
                "jd_text_snippet": jd_text[:100] + "...",
            })
        else:
            # Re-use process_and_create_application logic
            from routers.applications import process_and_create_application

            req_payload = ApplicationCreateRequest(
                company=company,
                role=role,
                jd_text=jd_text,
                source=source,
            )
            created_app = await process_and_create_application(req_payload, db)

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
