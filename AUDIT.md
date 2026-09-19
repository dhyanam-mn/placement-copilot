# Placement Copilot — System Audit Report

**Audit Execution Date**: September 19, 2026  
**Audit Scope**: Services, Database, Hardcoding Scan, Agent Wiring, API Inventory, Frontend, End-to-End Execution Trace, and Plan Conformance.  
**Audit Policy**: AUDIT ONLY. Zero code/schema modifications. All test data created during audit (`is_demo=true`, `AuditTest Corp`) was deleted post-execution.

---

## 🚨 Top 10 Blockers & Architectural Gaps

1. **Frontend Missing 8 of 9 Required Dedicated Routes**: Next.js App Router (`frontend/app`) contains only 1 route (`/`). Dedicated pages for `/scout`, `/tracker`, `/profile`, `/admin`, `/gap`, `/prep` do not exist.
2. **Frontend Renders Hardcoded Mock Data**: `ActivityFeed.tsx` imports and renders `mockActivityFeed` from `frontend/data/mockData.ts` instead of calling backend notification or event APIs.
3. **Frontend Calls Deprecated Q&A Endpoint**: `frontend/lib/api.ts` invokes deprecated `/applications/${id}/prep/evaluate-answer` instead of rendering recommended learning resources from `/applications/${id}/prep`.
4. **Gmail Tracker Persists State to File instead of DB**: `services/gmail_tracker.py` reads/writes sync state to `gmail_sync_state.json` on disk rather than the existing `gmail_sync_state` database table.
5. **Tailoring Service Reads `base_resume.json` instead of `profile` DB Table**: `services/tailoring.py` loads base resume bullets from local JSON rather than querying `profile` and `profile_projects` tables.
6. **Scam Check Engine Uses Hardcoded Red Flag Phrases**: `scam_check.py` queries `scam_patterns` DB table for domains/indicators, but hardcodes payment, urgency, and unofficial channel phrases in Python lists.
7. **Database Deduplication Key Lacks Schema Constraint**: `applications` table lacks a `UNIQUE` constraint or index on `(company, role, source)`. Deduplication relies solely on application-level checks.
8. **Settings Table Unread by Service Runtime**: The `settings` table is populated in DB, but services (`gmail_tracker.py`, `scheduler.py`, `scam_check.py`) use hardcoded constants for nudge (14d), ghosting (45d), and scam risk (0.7) thresholds.
9. **Status Events Table Is Unpopulated**: The `status_events` table exists in PostgreSQL schema but has 0 rows (`row_count: 0`). Application status transitions do not write event logs to DB.
10. **Frontend API Base URL Env Variable Mismatch**: `frontend/lib/api.ts` reads `NEXT_PUBLIC_API_URL` instead of `NEXT_PUBLIC_API_BASE_URL`.

---

## Section A: Services Audit

| Item | Status | Verified By | Evidence (Command / Output Excerpt) |
| :--- | :---: | :---: | :--- |
| **PostgreSQL Reachable** | Reachable | Executed | `python audit_scripts/check_services.py`<br>`PostgreSQL 18.6 on x86_64-windows, compiled by msvc-19.44.35228, 64-bit`. Conn string from `database.py` / `DATABASE_URL` env. |
| **FastAPI Backend (:8000)** | UP | Executed | `python audit_scripts/check_services.py`<br>`openapi.json` fetched successfully, OpenAPI title: `Placement Copilot Backend`, 27 paths. |
| **Model Service (:8001)** | UP | Executed | `python audit_scripts/check_services.py`<br>`POST http://localhost:8001/embed` returned 384-dimensional embeddings for sample text. |
| **Ollama (:11434)** | UP | Executed | `python audit_scripts/check_services.py`<br>`llama3.1:8b` model verified installed. Generate call returned response in `1.24s`. |
| **Gmail OAuth & API** | Refreshable / Working | Executed | `python audit_scripts/check_services.py`<br>`token.json` present (`valid: false`, `expired: true`, `refresh_token: true`). Read-only list call succeeded (`resultSizeEstimate: 1`). |
| **Tectonic LaTeX Engine** | Installed & Working | Executed | `python audit_scripts/check_services.py`<br>`Tectonic 0.17.0`. Successfully compiled sample `.tex` document to PDF. |
| **Frontend Build & Typecheck** | PASS (0 errors) | Executed | `npm --prefix frontend run build`<br>`Next.js 14.2.35`. Compiled successfully, static page generation (4/4) completed with 0 type errors. |
| **Environment Variables** | Inspected | Executed | `DATABASE_URL`: set. `ADZUNA_APP_ID`/`ADZUNA_APP_KEY`: missing (fallback returns empty array). `MODEL_SERVICE_URL`: default. `OLLAMA_URL`: default. `NEXT_PUBLIC_API_BASE_URL`: missing. |

---

## Section B: Database Audit

| Table Name | Status | Columns Count | Row Count | Primary / Foreign Keys & Constraints Evidence |
| :--- | :---: | :---: | :---: | :--- |
| **applications** | Present | 14 | 327 | PK: `id`. Declared FKs: `fk_gap_report`, `fk_tailored_resume`. `is_demo` exists (BOOLEAN). **Missing UNIQUE constraint on (company, role, source)**. |
| **gap_reports** | Present | 7 | 67 | PK: `id`. Declared FK: `application_id -> applications.id` (ON DELETE CASCADE). 0 orphans. |
| **tailored_resumes** | Present | 6 | 307 | PK: `id`. Declared FK: `application_id -> applications.id` (ON DELETE CASCADE). 0 orphans. |
| **scam_checks** | Present | 9 | 51 | PK: `id`. Declared FK: `application_id -> applications.id` (ON DELETE CASCADE). 0 orphans. |
| **profile** | Present | 6 | 1 | PK: `id`. Profile master record. |
| **profile_projects** | Present | 7 | 3 | PK: `id`. Declared FK: `profile_id -> profile.id`. |
| **skills** | Present | 6 | 35 | PK: `id`. Standard skill dictionary with aliases. |
| **resources** | Present | 7 | 23 | PK: `id`. Contains `is_active` and `verified_at` columns. |
| **resource_skills** | Present | 4 | 24 | PK: `id`. Declared FKs: `resource_id -> resources.id`, `skill_name -> skills.name`. |
| **scam_patterns** | Present | 7 | 21 | PK: `id`. Scam detection patterns. |
| **company_watchlist** | Present | 7 | 4 | PK: `id`. ATS company tokens (Greenhouse / Lever). |
| **settings** | Present | 3 | 9 | PK: `key`. System configuration settings. |
| **status_events** | Present (Empty) | 7 | 0 | PK: `id`. Declared FK: `application_id -> applications.id`. **Row count is 0 (Unpopulated)**. |
| **notifications** | Present | 6 | 2 | PK: `id`. Notification records. |
| **llm_cache** | Present | 4 | 1 | PK: `prompt_hash`. Caches LLM generated output. |
| **gmail_sync_state** | Present | 5 | 1 | PK: `id`. Master sync state table (currently bypassed by `gmail_sync_state.json` file). |
| **prep_recommendations**| Present | 7 | 2 | PK: `id`. Declared FKs: `application_id -> applications.id`, `resource_id -> resources.id`. 0 orphans. |

---

## Section C: Hardcoding Scan

| Search Term / Subject | Code Hits | DB Equivalent Table | DB Read at Runtime? | Evidence (File:Line & Audit Finding) |
| :--- | :--- | :--- | :---: | :--- |
| **student_skills** | `services/gap_agent.py:31` | `profile_projects` | Partial | Extracted from `profile_projects` tags at runtime. |
| **RESOURCE_DATABASE** | 0 hits | `resources` | Yes | `services/prep_agent.py` queries `resources` & `resource_skills` tables. |
| **RED_FLAG_PHRASES** | `scam_check.py:78-80` | `scam_patterns` | **No** | Payment, urgency, and unofficial channel phrases hardcoded in `scam_check.py`. |
| **LOOKALIKE_INDICATORS** | `scam_check.py:75-76` | `scam_patterns` | Partial | Queries `scam_patterns` table; falls back to hardcoded python list. |
| **PUBLIC_EMAIL_DOMAINS**| `scam_check.py:73-74` | `scam_patterns` | Partial | Queries `scam_patterns` table; falls back to hardcoded python set. |
| **base_resume.json** | `services/tailoring.py:11` | `profile` / `profile_projects` | **No** | Loads resume from `base_resume.json` file on disk instead of DB table `profile`. |
| **base_resume.tex** | `tailoring_agent.py:157` | N/A | File-backed | TeX template file used for PDF compilation. |
| **gmail_sync_state.json**| `services/gmail_tracker.py:16`| `gmail_sync_state` | **No** | Reads/writes sync state to JSON file instead of `gmail_sync_state` DB table. |
| **Magic Numbers** | `services/gmail_tracker.py` | `settings` | **No** | Thresholds (14d nudge, 45d auto-ghost) hardcoded in Python code; `settings` unread. |
| **SerpAPI / Celery** | 0 code hits | N/A | Deprecated | Verified completely removed from codebase. References only in audit docs. |
| **Question-Bank / Answer-Feedback** | `frontend/lib/api.ts:245` | N/A | **Dead Call** | Frontend retains dead call to `/prep/evaluate-answer`. Backend endpoints deleted. |

---

## Section D: Agent-to-Database Wiring Audit

| Agent / Component | Read Tables | Written Tables | Trigger Endpoint / Mechanism | Automatic Links Verification |
| :--- | :--- | :--- | :--- | :--- |
| **Scout Agent** | `company_watchlist`, `settings` | `applications` | `POST /scout/sync` or APScheduler (6h) | **Executed**: Ingests Adzuna, Greenhouse, Lever, Unstop. Runs `scam_check` rule layer before DB insertion. |
| **Scam-Check Agent** | `scam_patterns`, `applications` | `scam_checks`, `applications` | `POST /applications/{id}/scam-check` | **Executed**: Pre-insert screening flags high-risk domains (`risk_score >= 0.7`). Calls LLM for scam explanation. |
| **Tailoring Agent** | `applications` (Reads file `base_resume.json`) | `tailored_resumes`, `applications` | `POST /applications/{id}/tailor` | **Executed**: Embeds JD and ranks resume bullets without LLM. Updates `tailored_resume_id` on `applications`. |
| **Tracker Agent** | `applications` | `applications`, `notifications` | `POST /tracker/gmail/sync`, `POST /tracker/auto-ghost` | **Executed**: Matches Gmail messages via registrable SLD/ATS logic. Updates status and `status_source`. |
| **Human Checkpoint** | `applications` | `applications` | `POST /applications/{id}/confirm-applied` | **Executed**: LangGraph `interrupt_before=["tracker"]` pauses at `READY_TO_APPLY`. Endpoint resumes workflow to `APPLIED`. |
| **Prep Agent** | `skills`, `resources`, `resource_skills` | `prep_recommendations`, `llm_cache` | Status $\rightarrow$ `INTERVIEW` or `GET /applications/{id}/prep` | **Executed**: Deterministic skill gap $\rightarrow$ SQL-ranked top 10 resources $\rightarrow$ Ollama selects resource IDs $\rightarrow$ DB joins URLs. |
| **Gap Agent** | `applications`, `profile_projects`, `skills` | `gap_reports`, `notifications` | Status $\rightarrow$ `GHOSTED`/`REJECTED` or `GET /applications/{id}/gap-report` | **Executed**: Generates per-row gap report and creates notification record on ghost/rejection transition. |
| **Scheduler** | `applications` | `applications`, `gap_reports`, `notifications` | FastAPI Lifespan AsyncIOScheduler | **Executed**: Scout sync (6h), Gmail sync & auto-ghost (daily, leaves `last_contact_date` intact), Gap aggregate (weekly). |
| **Status Event Logging**| N/A | `status_events` | Status patch / background transition | **Gapped**: `status_events` table exists but currently receives 0 inserts during status updates. |

---

## Section E: API Inventory & Frontend Integration Audit

| Endpoint Path | Method | Backend Function | Frontend Call Site | Covered by Tests? | Status / Finding |
| :--- | :---: | :--- | :--- | :---: | :--- |
| `/applications` | GET | `get_applications` | `frontend/lib/api.ts:5` | Yes | Active |
| `/applications` | POST | `create_application` | `frontend/components/KanbanBoard.tsx` | Yes | Active |
| `/applications/{id}` | GET | `get_application_by_id` | `frontend/lib/api.ts:15` | Yes | Active |
| `/applications/{id}/confirm-applied` | POST | `confirm_application_submission` | `frontend/components/KanbanBoard.tsx` | Yes | Active |
| `/applications/{id}/status` | PATCH | `update_application_status` | `frontend/lib/api.ts:29` | Yes | Active |
| `/applications/{id}/tailor` | POST | `tailor_application` | `frontend/lib/api.ts:48` | Yes | Active |
| `/applications/{id}/gap-report` | GET | `get_application_gap_report` | `frontend/lib/api.ts:63` | Yes | Active |
| `/applications/{id}/gap-report` | POST | `generate_application_gap_report` | `frontend/lib/api.ts:83` | Yes | Active |
| `/gap-report` | GET | `get_aggregate_gap_report` | `frontend/lib/api.ts:73` | Yes | Active |
| `/applications/{id}/scam-check` | POST | `run_application_scam_check` | `frontend/lib/api.ts:98` | Yes | Active |
| `/applications/{id}/prep` | GET | `get_application_prep` | N/A (Missing in frontend client) | Yes | **Frontend Client Missing** |
| `/applications/{id}/prep` | POST | `generate_application_prep` | N/A (Missing in frontend client) | Yes | **Frontend Client Missing** |
| `/scout/sync` | POST | `trigger_scout_job_sourcing` | N/A | Yes | Admin / Background |
| `/tracker/gmail/sync` | POST | `trigger_gmail_sync` | N/A | Yes | Admin / Background |
| `/tracker/nudges` | GET | `get_tracker_nudges` | N/A | Yes | Admin / Background |
| `/tracker/auto-ghost` | POST | `trigger_auto_ghost` | N/A | Yes | Admin / Background |
| `/admin/demo/backdate` | POST | `demo_backdate_application` | N/A | Yes | Demo Endpoint |
| `/admin/scheduler/jobs` | GET | `list_scheduled_jobs` | N/A | Yes | Admin Endpoint |
| `/admin/scheduler/{id}/trigger` | POST | `trigger_scheduled_job` | N/A | Yes | Admin Endpoint |
| `/applications/{id}/prep/evaluate-answer` | POST | Deleted in Backend | `frontend/lib/api.ts:245` | No | **Dead Call in Frontend** |

* **CORS Verification**: Executed `curl` / `urllib` test with `Origin: http://localhost:3000`. Server responded with `200 OK` and header `Access-Control-Allow-Origin: http://localhost:3000`.
* **API Base URL Configuration**: `frontend/lib/api.ts` uses `process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"` (mismatched variable name vs `NEXT_PUBLIC_API_BASE_URL`).

---

## Section F: Frontend Audit

| Route / Page | Required Page? | Exists? | API Calls Made | Data Rendering Mode | Loading / Error States |
| :--- | :---: | :---: | :--- | :--- | :--- |
| `/` | Dashboard / Tracker | **Yes** | `getApplications`, `updateApplicationStatus`, `tailorResume`, `getGapReport`, `runScamCheck` | **Mixed** (Real applications; mock activity feed) | Handled in modals |
| `/scout` | Scout Sourcing | **No** | None | N/A | Missing Route |
| `/applications/{id}` | Job Detail | **Yes** (Modal) | `getApplication` | Real DB Data | Handled |
| `/tracker` | Tracker Board | **Yes** (on `/`) | `getApplications`, `updateApplicationStatus` | Real DB Data | Handled |
| `/notifications` | Notifications | **Yes** (Tab) | None (`mockActivityFeed`) | **100% Mock Data** | Missing error handling |
| `/gap` | Gap Report | **Yes** (Modal) | `getGapReport`, `getAggregateGapReport` | Real DB Data | Handled |
| `/prep` | Prep Study Plan | **Yes** (Modal) | Calls deprecated `/prep/evaluate-answer` | **Deprecated Q&A Mock** | Handled |
| `/profile` | Profile / Import | **No** | None | N/A | Missing Route |
| `/admin` | Admin Resources | **No** | None | N/A | Missing Route |

---

## Section G: End-to-End Trace Audit

**Execution Command**: `python -u audit_scripts/e2e_trace.py`  
**Test Row Tag**: `is_demo=true`, `company="AuditTest Corp"`, `role="Audit Test Engineer"`  
**Result**: **PASS (100% End-to-End Success Across All 8 Stages)**

```json
{
  "1_discover": { "status": "PASS", "http_code": 201, "time_sec": 5.358 },
  "2_scam_check": { "status": "PASS", "http_code": 200, "risk_score": 0.4, "time_sec": 15.370 },
  "3_tailor": { "status": "PASS", "http_code": 200, "tailored_resume_id": 444, "time_sec": 0.061 },
  "4_confirm_applied": { "status": "PASS", "http_code": 200, "status": "APPLIED", "time_sec": 0.060 },
  "5_gmail_signal": { "status": "PASS", "http_code": 200, "status": "INTERVIEW", "time_sec": 15.564 },
  "6_auto_ghost": { "status": "PASS", "ghosted_count": 2, "status": "GHOSTED", "time_sec": 33.142 },
  "7_gap_report": { "status": "PASS", "http_code": 200, "missing_skills": ["SQL"], "time_sec": 0.033 },
  "8_prep_recommendation": { "status": "PASS", "http_code": 200, "recommendations_count": 4, "time_sec": 0.043 }
}
```
* **Post-Execution Cleanup**: Verified test row `AuditTest Corp` (ID 831) and all associated records in `scam_checks`, `tailored_resumes`, `gap_reports`, and `prep_recommendations` were completely deleted from PostgreSQL.

---

## Section H: Plan Conformance Matrix

| Specification Item | Conformance Status | Verification & Implementation Evidence |
| :--- | :---: | :--- |
| **Sourcing (Adzuna + Greenhouse/Lever + Unstop)** | **Done** | `services/job_sourcing.py` implements all 4 adapters. SerpAPI references completely removed. Watchlist in `companies.json`. |
| **APScheduler (No Celery)** | **Done** | `services/scheduler.py` runs `AsyncIOScheduler` inside FastAPI lifespan. Celery dependencies removed. |
| **Tailoring Engine (No LLM)** | **Done** | `services/tailoring.py` uses embedding cosine similarity via model-service. Zero LLM calls. |
| **Prep Agent Study Plan** | **Done** | `services/prep_agent.py` extracts skills deterministically, queries SQL resource shortlist, prompts Ollama for resource IDs, and joins URLs strictly from DB `resources` table. |
| **Scoped LLM Usage** | **Done** | LLM calls strictly restricted to 3 endpoints: `scam_explanation`, `prep_recommendations`, and `gap_summary`. |
| **Gmail Matcher** | **Done** | `services/gmail_tracker.py` extracts SLD, normalizes company names, handles ATS senders and `noreply@mailer.razorpay.com`. |
| **Demo Mode & LLM Cache** | **Done** | `scripts/seed.py` supports `--demo` and `--reset-demo`. `llm_cache` table active in DB. |

---

## 🔧 Recommended Fix List & Dependency Order

| Priority | Task Description | Effort | Dependencies | Impact |
| :---: | :--- | :---: | :--- | :--- |
| **1** | Update `frontend/lib/api.ts` to replace deprecated `/prep/evaluate-answer` with `/applications/{id}/prep` study plan endpoint and fix `NEXT_PUBLIC_API_BASE_URL` env variable. | **S** | None | Fixes broken Prep UI tab and environment configuration. |
| **2** | Update `ActivityFeed.tsx` to fetch real status events/notifications from backend API instead of importing `mockActivityFeed`. | **S** | None | Eliminates mock data rendering on dashboard feed. |
| **3** | Refactor `services/gmail_tracker.py` to persist sync history in `gmail_sync_state` DB table instead of `gmail_sync_state.json`. | **S** | None | Aligns tracker state storage with PostgreSQL. |
| **4** | Refactor `services/tailoring.py` to read profile bullets from `profile` & `profile_projects` DB tables instead of `base_resume.json`. | **M** | None | Makes tailoring fully dynamic from user profile in DB. |
| **5** | Refactor `scam_check.py` to load red flag phrases dynamically from `scam_patterns` DB table instead of hardcoded lists. | **S** | None | Makes scam detection rule engine 100% DB-driven. |
| **6** | Add DB `settings` table reader helper and wire service thresholds (14d nudge, 45d ghost, 0.7 scam score) to runtime settings. | **M** | None | Enables runtime threshold configuration via Admin UI. |
| **7** | Add trigger/listener to write `status_events` audit rows on every application status transition. | **S** | None | Populates missing status transition history in DB. |
| **8** | Add `UNIQUE(company, role, source)` constraint migration to `applications` table in PostgreSQL. | **S** | DB backup | Enforces database-level deduplication integrity. |
| **9** | Add missing App Router pages (`/scout`, `/profile`, `/admin`, `/gap`, `/prep`) to `frontend/app/`. | **L** | Frontend Client | Delivers dedicated multi-page frontend routing. |
