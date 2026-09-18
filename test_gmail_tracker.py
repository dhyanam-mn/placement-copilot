import sys
import os
import unittest
import asyncio
from datetime import datetime, timezone

# Ensure root workspace is at head of sys.path
root_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, root_dir)

# Evict conflicting model-service schemas if loaded
if "schemas" in sys.modules and not hasattr(sys.modules["schemas"], "ApplicationStatusPatchRequest"):
    del sys.modules["schemas"]

from database import SessionLocal
from models import Application, GapReport
from services.gmail_tracker import (
    classify_email,
    match_email_to_application,
    sync_gmail_tracker,
    load_sync_state,
)

class TestGmailTrackerAgent(unittest.TestCase):

    def setUp(self):
        self.db = SessionLocal()
        # Seed test application in DB
        self.app = Application(
            company="Acme Corp",
            role="Backend Engineer",
            jd_text="Python FastAPI PostgreSQL SQL DSA",
            source="serpapi",
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
        if hasattr(self, 'app_id') and self.app_id:
            to_del = self.db.query(Application).filter(Application.id == self.app_id).first()
            if to_del:
                self.db.delete(to_del)
                self.db.commit()
        self.db.close()

    # --- 1. Deterministic Classifier Tests ---

    def test_classify_oa_invite(self):
        cat_status = classify_email(
            subject="Invitation to Online Assessment - Acme Corp",
            body="Please complete your coding test on HackerRank within 48 hours."
        )
        self.assertIsNotNone(cat_status)
        category, status_enum = cat_status
        self.assertEqual(category, "assessment")
        self.assertEqual(status_enum, "OA_INVITE")

    def test_classify_interview_invitation(self):
        cat_status = classify_email(
            subject="Acme Corp: Technical Interview Schedule",
            body="We would like to invite you for a technical interview next week."
        )
        self.assertIsNotNone(cat_status)
        category, status_enum = cat_status
        self.assertEqual(category, "interview")
        self.assertEqual(status_enum, "INTERVIEW")

    def test_classify_rejection_email(self):
        cat_status = classify_email(
            subject="Status of your Acme Corp application",
            body="Thank you for applying. Unfortunately, we have decided to move forward with other candidates."
        )
        self.assertIsNotNone(cat_status)
        category, status_enum = cat_status
        self.assertEqual(category, "regret")
        self.assertEqual(status_enum, "REJECTED")

    def test_classify_offer_email(self):
        cat_status = classify_email(
            subject="Job Offer from Acme Corp",
            body="We are pleased to offer you the position of Backend Engineer."
        )
        self.assertIsNotNone(cat_status)
        category, status_enum = cat_status
        self.assertEqual(category, "offer")
        self.assertEqual(status_enum, "OFFER")

    def test_classify_unrelated_email(self):
        cat_status = classify_email(
            subject="Weekly Newsletter - Tech Trends 2026",
            body="Here are the top tech stories of the week."
        )
        self.assertIsNone(cat_status)

    # --- 2. Company & Application Matching Tests ---

    def test_match_application_by_company_in_sender(self):
        matched = match_email_to_application(
            self.db,
            sender="recruiter@acmecorp.com",
            subject="Update on your application",
            body="Hello from Acme Corp team."
        )
        self.assertIsNotNone(matched)
        self.assertEqual(matched.id, self.app_id)

    def test_match_application_by_company_in_subject(self):
        matched = match_email_to_application(
            self.db,
            sender="hr-noreply@jobs-portal.com",
            subject="Acme Corp - Application Update",
            body="Your application for Backend Engineer is received."
        )
        self.assertIsNotNone(matched)
        self.assertEqual(matched.id, self.app_id)

    def test_unmatched_email(self):
        matched = match_email_to_application(
            self.db,
            sender="contact@unknown-company.io",
            subject="General Inquiry",
            body="Random email content."
        )
        self.assertIsNone(matched)

    # --- 3. Full Sync Pipeline & Gap Report Trigger Tests ---

    def test_sync_pipeline_oa_invite_update(self):
        mock_msgs = [{
            "id": "msg_oa_101",
            "history_id": "1001",
            "sender": "careers@acmecorp.com",
            "subject": "Acme Corp Online Assessment Invitation",
            "body": "Please complete your HackerRank test."
        }]

        result = asyncio.run(sync_gmail_tracker(self.db, mock_messages=mock_msgs))
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["messages_classified_and_matched"], 1)

        # Refresh database state
        self.db.refresh(self.app)
        self.assertEqual(self.app.status, "OA_INVITE")
        self.assertEqual(self.app.status_source, "gmail_auto")

    def test_sync_pipeline_rejection_triggers_gap_report(self):
        mock_msgs = [{
            "id": "msg_rej_102",
            "history_id": "1002",
            "sender": "careers@acmecorp.com",
            "subject": "Update on Acme Corp application",
            "body": "Unfortunately, we are pursuing other candidates."
        }]

        result = asyncio.run(sync_gmail_tracker(self.db, mock_messages=mock_msgs))
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["messages_classified_and_matched"], 1)

        # Verify application status updated to REJECTED with gmail_auto
        self.db.refresh(self.app)
        self.assertEqual(self.app.status, "REJECTED")
        self.assertEqual(self.app.status_source, "gmail_auto")

        # Verify per-row gap report was automatically generated and linked
        self.assertIsNotNone(self.app.gap_report_id)
        gap_report = self.db.query(GapReport).filter(GapReport.id == self.app.gap_report_id).first()
        self.assertIsNotNone(gap_report)
        self.assertEqual(gap_report.application_id, self.app_id)
        self.assertEqual(gap_report.report_type, "per_row")

if __name__ == "__main__":
    unittest.main()
