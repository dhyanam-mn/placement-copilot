-- ============================================================
-- Placement Copilot — PostgreSQL Schema
-- Team: Barely Made It (CC-4180) | TAM-VIT Hackathon
-- Hour 0 shared contract — reviewed and committed jointly by
-- Aadya (Frontend + Deterministic Backend) and Dhyanam (Model Service)
-- ============================================================

-- ---------- Enum types ----------

-- Full lifecycle a single application can move through.
-- GHOSTED and REJECTED are both terminal, kept distinct on purpose
-- (see README / report section 3.3 — Tracker Agent).
CREATE TYPE application_status AS ENUM (
    'DISCOVERED',      -- Scout Agent found and matched a JD
    'READY_TO_APPLY',   -- Tailoring Agent has reordered the resume for this JD
    'APPLIED',
    'OA_INVITE',
    'INTERVIEW',
    'REJECTED',         -- explicit rejection email detected
    'GHOSTED',           -- no contact for 45+ days, auto-set
    'OFFER'
);

-- How a status transition was made — lets us honestly report
-- what fraction of updates were automated vs manual.
CREATE TYPE status_source_type AS ENUM (
    'gmail_auto',
    'auto_ghost',
    'manual'
);

-- ---------- Core table ----------

CREATE TABLE applications (
    id                   SERIAL PRIMARY KEY,

    -- What the job is
    company              TEXT NOT NULL,
    role                 TEXT NOT NULL,
    jd_text              TEXT NOT NULL,               -- full job description, used by Scout/Tailoring
    source               TEXT NOT NULL CHECK (source IN ('serpapi', 'unstop')),

    -- Where it stands
    status               application_status NOT NULL DEFAULT 'DISCOVERED',
    status_source        status_source_type,

    -- Scout Agent output
    match_score          REAL,                        -- cosine similarity score from model-service /embed

    -- Linked artifacts (nullable — set once the relevant agent has run)
    tailored_resume_id   INTEGER,                     -- FK to tailored_resumes, set by Tailoring Agent
    gap_report_id        INTEGER,                     -- FK to gap_reports, set on GHOSTED/REJECTED

    -- Timing — last_contact_date drives the 45-day auto-ghost check
    last_contact_date    TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_updated         TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Indexes for the two query patterns that matter most:
-- filtering the Kanban board by status, and the daily staleness sweep.
CREATE INDEX idx_applications_status ON applications (status);
CREATE INDEX idx_applications_last_contact_date ON applications (last_contact_date);

-- Auto-update last_updated on every row change, so no agent has to
-- remember to set it manually.
CREATE OR REPLACE FUNCTION set_last_updated()
RETURNS TRIGGER AS $$
BEGIN
    NEW.last_updated = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_applications_last_updated
BEFORE UPDATE ON applications
FOR EACH ROW
EXECUTE FUNCTION set_last_updated();

-- ---------- Tailored resumes (Tailoring Agent output) ----------

CREATE TABLE tailored_resumes (
    id              SERIAL PRIMARY KEY,
    application_id  INTEGER NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
    resume_data     JSONB NOT NULL,   -- reordered bullets/sections, same wording as base resume
    match_score     REAL,             -- score used to decide the ordering, for traceability
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE applications
    ADD CONSTRAINT fk_tailored_resume
    FOREIGN KEY (tailored_resume_id) REFERENCES tailored_resumes(id);

-- ---------- Gap reports (Gap Agent output — per-row and aggregate) ----------

CREATE TABLE gap_reports (
    id              SERIAL PRIMARY KEY,
    application_id  INTEGER REFERENCES applications(id) ON DELETE CASCADE, -- NULL for aggregate reports
    report_type     TEXT NOT NULL CHECK (report_type IN ('per_row', 'aggregate')),
    summary_text    TEXT NOT NULL,     -- the LLM-generated plain-English summary
    details         JSONB,             -- underlying computed stats (deterministic, not LLM-generated)
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE applications
    ADD CONSTRAINT fk_gap_report
    FOREIGN KEY (gap_report_id) REFERENCES gap_reports(id);

CREATE INDEX idx_gap_reports_application_id ON gap_reports (application_id);

-- ---------- Scam checks (Scam-Check Agent output) ----------

CREATE TABLE scam_checks (
    id                SERIAL PRIMARY KEY,
    application_id    INTEGER REFERENCES applications(id) ON DELETE CASCADE, -- NULL if not tied to an application
    recruiter_name    TEXT,
    recruiter_domain  TEXT,
    risk_score        REAL NOT NULL,        -- deterministic rule-layer output, 0-1
    flagged_reasons   JSONB NOT NULL,        -- list of rule-based red flags that fired
    explanation_text  TEXT,                 -- LLM-phrased explanation of the flagged_reasons above
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_scam_checks_application_id ON scam_checks (application_id);

-- ============================================================
-- Sample data — 5 rows, for both of you to sanity-check the
-- schema before wiring in real agents.
-- ============================================================

INSERT INTO applications
    (company, role, jd_text, source, status, status_source, match_score, last_contact_date)
VALUES
    ('DronaMaps', 'Computer Vision Intern',
     'Looking for an intern experienced in object detection, GeoTIFF/satellite imagery processing, and Python.',
     'unstop', 'INTERVIEW', 'gmail_auto', 0.87, now() - INTERVAL '3 days'),

    ('Razorpay', 'SDE Intern',
     'Backend engineering internship — REST APIs, SQL, distributed systems fundamentals.',
     'serpapi', 'OA_INVITE', 'gmail_auto', 0.61, now() - INTERVAL '10 days'),

    ('Zeta Suite', 'Software Engineer',
     'Full-stack role — React, Node.js, MongoDB, and cloud deployment experience preferred.',
     'serpapi', 'GHOSTED', 'auto_ghost', 0.72, now() - INTERVAL '50 days'),

    ('Skylark Labs', 'ML Engineer Intern',
     'Computer vision pipeline work — YOLO-family models, model deployment, edge inference.',
     'unstop', 'REJECTED', 'gmail_auto', 0.79, now() - INTERVAL '20 days'),

    ('Innovaccer', 'SDE-1',
     'Strong DSA fundamentals, system design basics, SQL, and one backend language.',
     'serpapi', 'DISCOVERED', NULL, 0.54, now());
