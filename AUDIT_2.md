# Placement Copilot — System Re-Audit Report (AUDIT_2.md)

**Audit Execution Date**: September 19, 2026  
**Scope**: Verification of Top 10 Blockers, Section A (Services), Section B (Database), Section C (Hardcoding), Section D (Agent Wiring), Section E (API Inventory), Section F (Frontend), Section G (E2E Trace), and Section H (Plan Conformance).  

---

## 🚨 Top 10 Blockers Status (vs. AUDIT.md)

| # | Blocker Item from AUDIT.md | Status in Re-Audit | Evidence & Empirical Verification |
| :-: | :--- | :---: | :--- |
| **1** | Frontend missing dedicated App Router pages | **FIXED** | `check_frontend.py` verified all 9 dedicated routes (`/`, `/scout`, `/applications/[id]`, `/tracker`, `/notifications`, `/gap`, `/prep`, `/profile`, `/admin`). `npm run build` compiled 11 static/dynamic routes with 0 errors. |
| **2** | Frontend renders hardcoded `mockActivityFeed` | **FIXED** | `ActivityFeed.tsx` deleted. `/notifications` page fetches live feed from `GET /notifications`. Zero mock data imports remaining in frontend. |
| **3** | Frontend calls deprecated Q&A `/prep/evaluate-answer` | **FIXED** | `PrepChat.tsx` deleted. `/prep` page calls `getPrepRecommendations` (`GET /applications/{id}/prep`) rendering SQL-ranked resources & URLs. |
| **4** | Gmail Tracker persists state to JSON file | **FIXED** | `services/gmail_tracker.py` rewritten to read/write state to `gmail_sync_state` DB table. `gmail_sync_state.json` file deleted. |
| **5** | Tailoring Service reads `base_resume.json` | **FIXED** | `services/tailoring.py` queries `profile` and `profile_projects` PostgreSQL tables dynamically to build resume bullet vectors. |
| **6** | Scam Check Engine uses hardcoded red flag lists | **FIXED** | `scam_check.py` loads patterns dynamically from `scam_patterns` DB table across all phrase categories (`payment_request`, `urgency_tactic`, `unofficial_communication`, etc.). |
| **7** | DB missing `UNIQUE(company, role, source)` constraint | **FIXED** | Added `uq_applications_company_role_source` constraint via migration. Verified in PostgreSQL schema via `check_database.py`. |
| **8** | DB `settings` table unread by service runtime | **FIXED** | `get_setting_value()` reads `settings` DB table dynamically for `ghost_threshold_days`, `nudge_threshold_days`, `scam_risk_threshold`, `scout_sync_interval_hours`. |
| **9** | `status_events` table unpopulated (0 rows) | **FIXED** | All status updates use centralized `set_status()` helper, inserting audit events into `status_events` table. Row count active in DB. |
| **10** | Frontend env var mismatch (`NEXT_PUBLIC_API_URL`) | **FIXED** | `frontend/lib/api.ts` uses `process.env.NEXT_PUBLIC_API_BASE_URL`. `frontend/.env.example` created with default value `http://localhost:8000`. |

---

## Section A: Services Re-Audit

| Item | Previous Status | Current Status | Evidence / Command Output Excerpt |
| :--- | :---: | :---: | :--- |
| **PostgreSQL Reachable** | Reachable | **FIXED / UP** | `python audit_scripts/check_services.py`<br>`PostgreSQL 18.6 on x86_64-windows`. Connection string loaded via `database.py`. |
| **FastAPI Backend (:8000)** | UP | **FIXED / UP** | `python audit_scripts/check_services.py`<br>FastAPI server running on `:8000`. `/openapi.json` fetched successfully (42 paths). |
| **Model Service (:8001)** | UP | **FIXED / UP** | `python audit_scripts/check_services.py`<br>`POST http://localhost:8001/embed` returned 384-dimensional embeddings. |
| **Ollama (:11434)** | UP | **FIXED / UP** | `urllib` test to `http://localhost:11434/api/tags` returned installed model `llama3.1:8b`. |
| **Gmail OAuth & API** | Refreshable | **FIXED / UP** | `token.json` present and refreshable. Read-only list call returned `200 OK` (`resultSizeEstimate: 1`). |
| **Tectonic LaTeX Engine** | Installed | **FIXED / UP** | `Tectonic 0.17.0` compiled sample `.tex` document to PDF. |
| **Frontend Build & Typecheck** | PASS | **FIXED / PASS** | `npm run build` completed with `Exit code: 0`. All 11 pages compiled with zero errors. |
| **Environment Variables** | Inspected | **FIXED / VERIFIED**| `DATABASE_URL` set. `NEXT_PUBLIC_API_BASE_URL` defined in `frontend/.env.example`. |

---

## Section B: Database Re-Audit

| Table Name | AUDIT.md Status | AUDIT_2.md Status | Row Count | Constraints & Integrity Verification |
| :--- | :---: | :---: | :---: | :--- |
| **applications** | Present | **FIXED** | 16 | PK: `id`. **Added `uq_applications_company_role_source` UNIQUE constraint**. Deduplicated. |
| **gap_reports** | Present | **VERIFIED** | 68 | PK: `id`. FK: `application_id -> applications.id`. 0 orphans. |
| **tailored_resumes**| Present | **VERIFIED** | 308 | PK: `id`. FK: `application_id -> applications.id`. 0 orphans. |
| **scam_checks** | Present | **VERIFIED** | 52 | PK: `id`. FK: `application_id -> applications.id`. 0 orphans. |
| **profile** | Present | **VERIFIED** | 1 | PK: `id`. Primary user profile. |
| **profile_projects**| Present | **VERIFIED** | 3 | PK: `id`. FK: `profile_id -> profile.id`. |
| **skills** | Present | **VERIFIED** | 35 | PK: `id`. Taxonomy of skill keywords and aliases. |
| **resources** | Present | **VERIFIED** | 23 | PK: `id`. Contains `is_active` and `verified_at` columns. |
| **resource_skills** | Present | **VERIFIED** | 24 | PK: `id`. FKs: `resource_id -> resources.id`, `skill_name -> skills.name`. |
| **scam_patterns** | Present | **VERIFIED** | 21 | PK: `id`. DB patterns for payment requests, urgency, domains. |
| **company_watchlist**| Present | **VERIFIED** | 4 | PK: `id`. Company tokens for Greenhouse and Lever. |
| **settings** | Present | **FIXED** | 9 | PK: `key`. Active thresholds (`ghost_threshold_days`, `scam_risk_threshold`, etc.). |
| **status_events** | Present (0 rows)| **FIXED** | 18 | PK: `id`. FK: `application_id -> applications.id`. **Populated on every status update**. |
| **notifications** | Present | **VERIFIED** | 12 | PK: `id`. Notification records. |
| **llm_cache** | Present | **VERIFIED** | 1 | PK: `prompt_hash`. Caches LLM outputs. |
| **gmail_sync_state**| Present | **FIXED** | 1 | PK: `id`. **Active sync state table (file storage removed)**. |
| **prep_recommendations**| Present | **VERIFIED** | 2 | PK: `id`. FKs to `applications` and `resources`. |

---

## Section C: Hardcoding Scan Re-Audit

| Subject | AUDIT.md Finding | AUDIT_2.md Status | Evidence |
| :--- | :--- | :---: | :--- |
| **RED_FLAG_PHRASES** | Hardcoded Python list | **FIXED** | `scam_check.py` loads red flag phrases dynamically from DB `scam_patterns` table. |
| **LOOKALIKE_INDICATORS**| Hardcoded Python fallback | **FIXED** | Loaded dynamically from DB `scam_patterns` table. |
| **PUBLIC_EMAIL_DOMAINS**| Hardcoded Python fallback | **FIXED** | Loaded dynamically from DB `scam_patterns` table. |
| **base_resume.json** | Loaded from JSON file | **FIXED** | `services/tailoring.py` queries `profile` & `profile_projects` DB tables. |
| **gmail_sync_state.json**| Saved to JSON file | **FIXED** | `services/gmail_tracker.py` uses DB `gmail_sync_state` table. JSON file deleted. |
| **Magic Numbers** | Unread `settings` table | **FIXED** | `get_setting_value()` reads runtime thresholds dynamically from `settings` DB table. |
| **Question-Bank** | Legacy frontend call | **FIXED** | `PrepChat.tsx` and dead call removed. Frontend calls `/prep` study plan endpoint. |

---

## Section D: Agent-to-Database Wiring Re-Audit

| Agent | Trigger Endpoint | Written Tables | Status |
| :--- | :--- | :--- | :---: |
| **Scout Agent** | `POST /scout/sync` or APScheduler | `applications` | **VERIFIED** |
| **Scam-Check Agent** | `POST /applications/{id}/scam-check` | `scam_checks`, `applications` | **VERIFIED** |
| **Tailoring Agent** | `POST /applications/{id}/tailor` | `tailored_resumes`, `applications` | **VERIFIED** |
| **Tracker Agent** | `POST /gmail/sync`, `POST /tracker/auto-ghost` | `applications`, `notifications` | **VERIFIED** |
| **Human Checkpoint** | `POST /applications/{id}/confirm-applied` | `applications` | **VERIFIED** |
| **Prep Agent** | `GET /applications/{id}/prep` | `prep_recommendations`, `llm_cache` | **VERIFIED** |
| **Gap Agent** | `GET /applications/{id}/gap-report` | `gap_reports`, `notifications` | **VERIFIED** |
| **Status Event Logging**| Transition via `set_status()` | `status_events` | **FIXED** |

---

## Section E: API Inventory Re-Audit

- **Total Endpoints in `/openapi.json`**: 64 active routes (including CRUD endpoints for `/profile`, `/resources`, `/skills`, `/scam-patterns`, `/watchlist`, `/settings`, `/notifications`, `/applications/{id}/events`, `/applications/{id}/scam-check`).
- **CORS Verification**: `curl` with `Origin: http://localhost:3000` returned `200 OK` with `Access-Control-Allow-Origin: http://localhost:3000`.
- **Frontend API Base URL**: `frontend/lib/api.ts` correctly reads `NEXT_PUBLIC_API_BASE_URL`.

---

## Section F: Frontend Routes Re-Audit

| Route | AUDIT.md Status | AUDIT_2.md Status | Data Source | Loading / Error States |
| :--- | :---: | :---: | :--- | :--- |
| `/` | Missing 8 routes | **FIXED** | `GET /applications` | Handled |
| `/scout` | Missing Route | **FIXED** | `POST /scout/sync`, `GET /applications` | Handled |
| `/applications/[id]` | Modal Only | **FIXED** | `GET /applications/{id}`, `GET /applications/{id}/events` | Handled |
| `/tracker` | Tab Only | **FIXED** | `POST /gmail/sync`, `GET /tracker/nudges` | Handled |
| `/notifications` | 100% Mock | **FIXED** | `GET /notifications` | Handled |
| `/gap` | Modal Only | **FIXED** | `GET /gap-report`, `POST /applications/{id}/gap-report` | Handled |
| `/prep` | Deprecated Q&A | **FIXED** | `GET /applications/{id}/prep`, `POST /applications/{id}/prep` | Handled |
| `/profile` | Missing Route | **FIXED** | `GET /profile`, `POST /profile/import` | Handled |
| `/admin` | Missing Route | **FIXED** | CRUD for resources, skills, scam patterns, settings | Handled |

---

## Section G: End-to-End Trace Re-Audit

**Execution Command**: `python audit_scripts/e2e_trace.py`  
**Test Row Tag**: `is_demo=false`, `company="AuditTest Corp"`, `role="Audit Test Engineer"`  
**Result**: **PASS (100% Success Across All 8 Stages)**

```json
{
  "1_discover": { "status": "PASS", "http_code": 201, "time_sec": 3.453 },
  "2_scam_check": { "status": "PASS", "http_code": 200, "risk_score": 0.4, "time_sec": 5.338 },
  "3_tailor": { "status": "PASS", "http_code": 200, "time_sec": 0.080 },
  "4_confirm_applied": { "status": "PASS", "http_code": 200, "status": "APPLIED", "time_sec": 0.201 },
  "5_gmail_signal": { "status": "PASS", "http_code": 200, "status": "INTERVIEW", "time_sec": 5.212 },
  "6_auto_ghost": { "status": "PASS", "status": "GHOSTED", "time_sec": 9.102 },
  "7_gap_report": { "status": "PASS", "http_code": 200, "time_sec": 0.019 },
  "8_prep_recommendation": { "status": "PASS", "http_code": 200, "time_sec": 0.031 }
}
```
* **Post-Trace Cleanup**: Verified test record `AuditTest Corp` was completely deleted from PostgreSQL.

---

## Section H: Plan Conformance Matrix

| Specification Item | Status | Verification & Evidence |
| :--- | :---: | :--- |
| **Sourcing (Adzuna + Greenhouse/Lever + Unstop)** | **Done** | `services/job_sourcing.py` implements all 4 adapters. Watchlist in DB `company_watchlist`. SerpAPI code deleted. |
| **APScheduler (No Celery)** | **Done** | `services/scheduler.py` runs `AsyncIOScheduler` inside FastAPI lifespan. Celery dependencies removed. |
| **Tailoring Engine (No LLM)** | **Done** | `services/tailoring.py` uses embedding cosine similarity via model-service. Reads DB `profile`. Zero LLM calls. |
| **Prep Agent Study Plan** | **Done** | `services/prep_agent.py` extracts skills deterministically, ranks resources via SQL, uses Ollama for resource IDs, joins URLs strictly from DB. |
| **Scoped LLM Usage** | **Done** | LLM calls strictly restricted to 3 endpoints: `scam_explanation`, `prep_recommendations`, and `gap_summary`. |
| **Gmail Matcher** | **Done** | `services/gmail_tracker.py` extracts SLD, normalizes company names, handles ATS senders and `noreply@mailer.razorpay.com`. |
| **Demo Mode & LLM Cache** | **Done** | `scripts/seed.py` supports `--demo` and `--reset-demo`. `llm_cache` table active in DB. |
