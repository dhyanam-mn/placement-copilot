import sys
import os
import unittest
import asyncio
from datetime import datetime, timezone, timedelta

# Ensure root workspace is at head of sys.path
root_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, root_dir)

# Evict conflicting model-service schemas if loaded
if "schemas" in sys.modules and not hasattr(sys.modules["schemas"], "ApplicationStatusPatchRequest"):
    del sys.modules["schemas"]

from database import SessionLocal
from models import Application, GapReport, Notification
from services.gmail_tracker import (
    classify_email,
    match_email_to_application,
    sync_gmail_tracker,
    load_sync_state,
    run_auto_ghost_sweep,
    get_stale_application_nudges,
    extract_second_level_label,
    normalize_company_name,
)

class TestGmailTrackerAgent(unittest.TestCase):

    def setUp(self):
        self.db = SessionLocal()
        from sqlalchemy import text
        self.db.execute(text("UPDATE applications SET tailored_resume_id = NULL, gap_report_id = NULL WHERE company ILIKE '%Razorpay%';"))
        self.db.execute(text("DELETE FROM applications WHERE company ILIKE '%Razorpay%';"))
        self.db.commit()

        # Seed test application in DB
        self.app = Application(
            company="Razorpay Software Pvt. Ltd.",
            role="Backend Engineer",
            jd_text="Python FastAPI PostgreSQL SQL DSA",
            source="adzuna",
            status="APPLIED",
            status_source="manual",
            match_score=0.75,
            last_contact_date=datetime.now(timezone.utc),
        )
        self.db.add(self.app)
        self.db.commit()
        self.db.refresh(self.app)
        self.app_id = self.app.id

    def tearDown(self):
        from sqlalchemy import text
        self.db.execute(text("UPDATE applications SET tailored_resume_id = NULL, gap_report_id = NULL WHERE company ILIKE '%Razorpay%';"))
        self.db.execute(text("DELETE FROM applications WHERE company ILIKE '%Razorpay%';"))
        self.db.commit()
        self.db.close()

    # --- 1. Deterministic Classifier Tests ---

    def test_classify_oa_invite(self):
        cat_status = classify_email(
            subject="Invitation to Online Assessment - Razorpay",
            body="Please complete your coding test on HackerRank within 48 hours."
        )
        self.assertIsNotNone(cat_status)
        category, status_enum = cat_status
        self.assertEqual(category, "assessment")
        self.assertEqual(status_enum, "OA_INVITE")

    def test_classify_rejection_email(self):
        cat_status = classify_email(
            subject="Status of your Razorpay application",
            body="Thank you for applying. Unfortunately, we have decided to move forward with other candidates."
        )
        self.assertIsNotNone(cat_status)
        category, status_enum = cat_status
        self.assertEqual(category, "regret")
        self.assertEqual(status_enum, "REJECTED")

    # --- 2. Advanced Domain & Company Matching Tests ---

    def test_match_by_subdomain_and_second_level_label(self):
        """Should match 'noreply@mailer.razorpay.com' to 'Razorpay Software Pvt. Ltd.' via SLD label 'razorpay'."""
        self.assertEqual(extract_second_level_label("mailer.razorpay.com"), "razorpay")
        self.assertEqual(normalize_company_name("Razorpay Software Pvt. Ltd."), "razorpay")

        matched = match_email_to_application(
            self.db,
            sender="Razorpay Careers <noreply@mailer.razorpay.com>",
            subject="Update on your application",
            body="Thank you for your interest in Backend Engineer."
        )
        self.assertIsNotNone(matched)
        self.assertEqual(matched.id, self.app_id)

    def test_match_ats_sender_by_display_name_and_subject(self):
        """ATS senders (greenhouse.io, lever.co) should be matched by display name or subject."""
        stripe_app = Application(
            company="UniqueStripeTestCorp",
            role="SWE Intern",
            jd_text="Go APIs Billing",
            source="greenhouse",
            status="APPLIED",
            match_score=0.88,
            last_contact_date=datetime.now(timezone.utc),
        )
        self.db.add(stripe_app)
        self.db.commit()
        self.db.refresh(stripe_app)

        try:
            matched = match_email_to_application(
                self.db,
                sender="UniqueStripeTestCorp via Greenhouse <no-reply@greenhouse.io>",
                subject="Invitation to Interview",
                body="We would love to schedule a technical interview."
            )
            self.assertIsNotNone(matched)
            self.assertEqual(matched.id, stripe_app.id)
        finally:
            self.db.delete(stripe_app)
            self.db.commit()

    def test_unmatched_email_logs_warning_and_returns_none(self):
        matched = match_email_to_application(
            self.db,
            sender="contact@unknown-company.io",
            subject="General Inquiry",
            body="Random email content."
        )
        self.assertIsNone(matched)

    # --- 3. Nudges & Auto-Ghost Tests ---

    def test_tracker_nudges_filtering(self):
        """get_stale_application_nudges should return applications stale past threshold (e.g. 14 days)."""
        self.app.last_contact_date = datetime.now(timezone.utc) - timedelta(days=20)
        self.db.commit()

        nudges_res = get_stale_application_nudges(self.db, threshold_days=14)
        self.assertEqual(nudges_res["threshold_days"], 14)
        self.assertGreaterEqual(nudges_res["total_nudges"], 1)

        found = any(n["id"] == self.app_id for n in nudges_res["nudges"])
        self.assertTrue(found)

    def test_auto_ghost_sweep_preserves_last_contact_date(self):
        """Auto-ghost at 45 days should update status to GHOSTED with status_source='auto_ghost', while preserving last_contact_date."""
        old_contact_date = datetime.now(timezone.utc) - timedelta(days=50)
        self.app.last_contact_date = old_contact_date
        self.db.commit()

        sweep_res = asyncio.run(run_auto_ghost_sweep(self.db))
        self.assertEqual(sweep_res["status"], "success")
        self.assertGreaterEqual(sweep_res["total_ghosted"], 1)

        self.db.refresh(self.app)
        self.assertEqual(self.app.status, "GHOSTED")
        self.assertEqual(self.app.status_source, "auto_ghost")
        # Verify last_contact_date was untouched
        self.assertEqual(self.app.last_contact_date, old_contact_date)

        # Verify Notification record was created
        notif = self.db.query(Notification).filter(Notification.content.contains("Razorpay")).first()
        self.assertIsNotNone(notif)
        self.db.delete(notif)
        self.db.commit()

if __name__ == "__main__":
    unittest.main()
