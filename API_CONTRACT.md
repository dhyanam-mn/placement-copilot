# API_CONTRACT.md

**Owner:** Aadya | **Runs on:** `http://localhost:8000` | **Consumed by:** the Next.js frontend

Field names and types below match `schema.sql` exactly. Endpoints marked **[calls model-service]** internally hit Dhyanam's service at `localhost:8001` per `MODEL_SERVICE_CONTRACT.md` — everything else is pure backend logic with no GPU dependency.

---

## GET /applications

List all applications, optionally filtered by status — backs the Kanban board.

**Query params:** `?status=INTERVIEW` (optional; one of the `application_status` enum values)

**Response**
```json
{
  "applications": [
    {
      "id": 1,
      "company": "DronaMaps",
      "role": "Computer Vision Intern",
      "source": "unstop",
      "status": "INTERVIEW",
      "status_source": "gmail_auto",
      "match_score": 0.87,
      "tailored_resume_id": 3,
      "gap_report_id": null,
      "last_contact_date": "2026-09-15T10:00:00Z",
      "last_updated": "2026-09-15T10:00:00Z",
      "created_at": "2026-09-01T09:00:00Z"
    }
  ]
}
```

---

## GET /applications/{id}

Single row detail — backs the card-click view.

**Response:** same shape as one item in the `applications` array above.

---

## POST /applications

Creates a new row — called by the Scout Agent flow after a job match. **[calls model-service /embed]**

**Request**
```json
{
  "company": "Innovaccer",
  "role": "SDE-1",
  "jd_text": "Strong DSA fundamentals, system design basics, SQL...",
  "source": "adzuna"
}
```

**Backend behavior:** calls `model-service POST /embed` with the JD text and the student's resume bullets, computes cosine similarity, stores the result as `match_score`, sets `status: DISCOVERED`.

**Response:** the created row, same shape as `GET /applications/{id}`.

---

## PATCH /applications/{id}/status

Updates status. Called by the Tracker Agent (Gmail classification, manual override) and the daily staleness job (auto-ghost).

**Request**
```json
{
  "status": "GHOSTED",
  "status_source": "auto_ghost"
}
```

**Backend behavior:**
- Updates `status` and `status_source`.
- `last_updated` is set automatically by the DB trigger — do not set it manually.
- If the new status is `GHOSTED` or `REJECTED`, automatically triggers `POST /applications/{id}/gap-report` (see below) — this is the "immediate per-row gap report" behavior.

**Response:** the updated row.

---

## POST /applications/{id}/tailor

Triggers the Tailoring Agent (TF-IDF/keyword reordering — **no LLM call**, no model-service call at all).

**Request:** empty body — operates on the row's existing `jd_text` and the student's base resume (stored separately, e.g. `base_resume.json` in the repo).

**Response**
```json
{
  "tailored_resume_id": 4,
  "resume_data": {
    "ordered_bullets": [
      { "project": "DronaMaps CV Pipeline", "bullet": "...", "score": 0.91 },
      { "project": "VLA Robotic System", "bullet": "...", "score": 0.44 }
    ]
  }
}
```
Also sets `applications.status` to `READY_TO_APPLY` and links `tailored_resume_id`.

---

## GET /applications/{id}/gap-report

Fetch the per-row gap report for a GHOSTED/REJECTED application.

**Response**
```json
{
  "id": 12,
  "application_id": 5,
  "report_type": "per_row",
  "summary_text": "JD required SQL and system design — neither appeared in the matched resume skills for this application.",
  "details": {
    "jd_required_skills": ["SQL", "system design", "DSA"],
    "matched_skills": ["DSA"],
    "missing_skills": ["SQL", "system design"]
  },
  "created_at": "2026-09-10T12:00:00Z"
}
```

---

## POST /applications/{id}/gap-report

Generates the per-row report (called automatically by the status PATCH above, or manually for testing). **[calls model-service /llm-generate, task_type: gap_summary]**

**Backend behavior:** computes `jd_required_skills` vs `matched_skills` deterministically (same keyword-extraction method as the Tailoring Agent), sends the computed stats to model-service to get `summary_text`, stores both in `gap_reports`.

**Response:** same shape as `GET /applications/{id}/gap-report`.

---

## GET /gap-report

Aggregate report across all GHOSTED/REJECTED rows — backs the Gap Report chart.

**Response**
```json
{
  "id": 20,
  "report_type": "aggregate",
  "summary_text": "3 of 4 SDE-tagged rejections happened at OA stage; CV-tagged roles show no OA-stage rejections.",
  "details": {
    "by_role_tag": {
      "SDE": { "total": 4, "rejected_at_oa": 3, "rejected_at_interview": 1 },
      "CV": { "total": 2, "rejected_at_oa": 0, "rejected_at_interview": 1 }
    }
  },
  "created_at": "2026-09-16T08:00:00Z"
}
```

---

## POST /applications/{id}/scam-check

Runs the Scam-Check Agent on a recruiter contact tied to this application. **[calls model-service /llm-generate, task_type: scam_explanation]**

**Request**
```json
{
  "recruiter_name": "Rohan Sharma",
  "recruiter_domain": "technova-careers.in",
  "claimed_company": "TechNova Solutions"
}
```

**Backend behavior:** runs the deterministic rule layer (domain mismatch check against `claimed_company`'s known domain, red-flag phrase scan) to compute `flagged_reasons` and `risk_score`. If `risk_score > 0`, sends `flagged_reasons` to model-service for `explanation_text`.

**Response**
```json
{
  "id": 7,
  "risk_score": 0.8,
  "flagged_reasons": [
    "sender domain does not match company's official domain",
    "requests processing fee before interview"
  ],
  "explanation_text": "This looks risky: the sender's email domain doesn't match TechNova's official domain, and asking for a processing fee before any interview is a common red flag."
}
```

---

## GET /applications/{id}/prep

Retrieves or generates learning resource recommendations for an application in `INTERVIEW` status.

**Response**
```json
{
  "application_id": 1,
  "recommendations": [
    {
      "id": 10,
      "application_id": 1,
      "resource_id": 2,
      "title": "Docker Deep Dive",
      "url": "https://docs.docker.com/",
      "reason": "Recommended resource to master containerization required for this role.",
      "est_hours": 4,
      "created_at": "2026-09-19T05:00:00Z"
    }
  ]
}
```

---

## POST /applications/{id}/prep

Manually triggers/regenerates learning resource recommendations for an application.

**Response**: Same schema as `GET /applications/{id}/prep`.

---

## Error shape (all endpoints)

```json
{
  "error": "not_found",
  "detail": "application id 999 does not exist"
}
```
Standard codes to use: `not_found` (404), `validation_error` (422), `model_service_unavailable` (502 — when a `[calls model-service]` endpoint can't reach `localhost:8001`).
