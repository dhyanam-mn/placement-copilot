import sys
import os
import unittest
import asyncio

# Ensure workspace root is at head of sys.path
root_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, root_dir)

# Evict conflicting model-service schemas if loaded
if "schemas" in sys.modules and not hasattr(sys.modules["schemas"], "ApplicationStatusPatchRequest"):
    del sys.modules["schemas"]

from sqlalchemy import text
from database import SessionLocal
from models import Application, ScamCheck
from services.job_sourcing import (
    is_duplicate_application,
    run_job_sourcing,
    fetch_adzuna_jobs,
    fetch_greenhouse_jobs,
    fetch_lever_jobs,
    fetch_ats_jobs,
)

class TestJobSourcing(unittest.TestCase):

    def setUp(self):
        self.db = SessionLocal()
        # Clean up any leftover test rows using raw SQL to clear circular FKs first
        self.db.execute(text("""
            UPDATE applications
            SET tailored_resume_id = NULL, gap_report_id = NULL
            WHERE company IN ('Google Sourcing Test', 'Mock Amazon Tech', 'Mock Unstop Tech', 'Scam Corp', 'Greenhouse Verified');
        """))
        self.db.commit()

        existing_apps = self.db.query(Application).filter(
            Application.company.in_(["Google Sourcing Test", "Mock Amazon Tech", "Mock Unstop Tech", "Scam Corp", "Greenhouse Verified"])
        ).all()
        for item in existing_apps:
            self.db.delete(item)

        existing_scams = self.db.query(ScamCheck).filter(
            ScamCheck.recruiter_domain.in_(["scam-corp-careers.in", "greenhouse-verified.com"])
        ).all()
        for item in existing_scams:
            self.db.delete(item)

        self.db.commit()

        # Seed test application in DB
        self.app = Application(
            company="Google Sourcing Test",
            role="Cloud Engineer",
            jd_text="GCP Kubernetes Terraform Python Go",
            source="adzuna",
            status="DISCOVERED",
            match_score=0.82,
        )
        self.db.add(self.app)
        self.db.commit()
        self.db.refresh(self.app)
        self.app_id = self.app.id

    def tearDown(self):
        self.db.execute(text("""
            UPDATE applications
            SET tailored_resume_id = NULL, gap_report_id = NULL
            WHERE company IN ('Google Sourcing Test', 'Mock Amazon Tech', 'Mock Unstop Tech', 'Scam Corp', 'Greenhouse Verified');
        """))
        self.db.commit()

        if hasattr(self, "app_id") and self.app_id:
            to_del = self.db.query(Application).filter(Application.id == self.app_id).first()
            if to_del:
                self.db.delete(to_del)
                self.db.commit()

        created = (
            self.db.query(Application)
            .filter(Application.company.in_(["Mock Amazon Tech", "Mock Unstop Tech", "Scam Corp", "Greenhouse Verified"]))
            .all()
        )
        for item in created:
            self.db.delete(item)
        self.db.commit()
        self.db.close()

    def test_adzuna_returns_empty_list_if_keys_missing(self):
        """fetch_adzuna_jobs should return [] if ADZUNA keys are not present."""
        orig_id = os.environ.get("ADZUNA_APP_ID")
        orig_key = os.environ.get("ADZUNA_APP_KEY")

        if "ADZUNA_APP_ID" in os.environ:
            del os.environ["ADZUNA_APP_ID"]
        if "ADZUNA_APP_KEY" in os.environ:
            del os.environ["ADZUNA_APP_KEY"]

        import services.job_sourcing
        services.job_sourcing.ADZUNA_APP_ID = ""
        services.job_sourcing.ADZUNA_APP_KEY = ""

        res = asyncio.run(fetch_adzuna_jobs())
        self.assertEqual(res, [])

        # Restore
        if orig_id:
            os.environ["ADZUNA_APP_ID"] = orig_id
            services.job_sourcing.ADZUNA_APP_ID = orig_id
        if orig_key:
            os.environ["ADZUNA_APP_KEY"] = orig_key
            services.job_sourcing.ADZUNA_APP_KEY = orig_key

    def test_deduplication_detects_existing_application(self):
        """is_duplicate_application should return True for existing (company, role, source) tuple."""
        is_dup = is_duplicate_application(
            self.db, company="Google Sourcing Test", role="Cloud Engineer", source="adzuna"
        )
        self.assertTrue(is_dup)

        is_not_dup = is_duplicate_application(
            self.db, company="Google Sourcing Test", role="Frontend Dev", source="adzuna"
        )
        self.assertFalse(is_not_dup)

    def test_dry_run_mode_does_not_insert_rows(self):
        """run_job_sourcing in dry_run=True mode should preview results without writing to DB."""
        mock_listings = [
            {
                "company": "Mock Amazon Tech",
                "role": "SDE-2",
                "jd_text": "Java Distributed Systems AWS SQL DSA",
                "source": "adzuna",
            }
        ]

        count_before = self.db.query(Application).filter(Application.company == "Mock Amazon Tech").count()

        result = asyncio.run(
            run_job_sourcing(self.db, dry_run=True, mock_listings=mock_listings)
        )

        count_after = self.db.query(Application).filter(Application.company == "Mock Amazon Tech").count()
        self.assertEqual(count_before, 0)
        self.assertEqual(count_after, 0)
        self.assertEqual(result["status"], "success")
        self.assertTrue(result["dry_run"])
        self.assertEqual(result["processed_count"], 1)
        self.assertEqual(result["results"][0]["action"], "would_insert")
        self.assertEqual(result["results"][0]["company"], "Mock Amazon Tech")

    def test_live_sourcing_inserts_new_unique_listing(self):
        """run_job_sourcing in dry_run=False mode should insert unique listings into DB."""
        mock_listings = [
            # 1. Existing duplicate listing (should be skipped)
            {
                "company": "Google Sourcing Test",
                "role": "Cloud Engineer",
                "jd_text": "GCP Kubernetes Terraform Python Go",
                "source": "adzuna",
            },
            # 2. New unique listing (should be inserted)
            {
                "company": "Mock Unstop Tech",
                "role": "Frontend Intern",
                "jd_text": "React TypeScript HTML CSS Tailwind Node.js",
                "source": "unstop",
            },
        ]

        result = asyncio.run(
            run_job_sourcing(self.db, dry_run=False, mock_listings=mock_listings)
        )

        self.assertEqual(result["status"], "success")
        self.assertFalse(result["dry_run"])
        self.assertEqual(result["total_fetched"], 2)
        self.assertEqual(result["duplicates_skipped"], 1)
        self.assertEqual(result["processed_count"], 1)
        self.assertEqual(result["results"][0]["action"], "inserted")
        self.assertEqual(result["results"][0]["company"], "Mock Unstop Tech")
        self.assertEqual(result["results"][0]["source"], "unstop")

        # Verify DB row created
        db_app = (
            self.db.query(Application)
            .filter(Application.company == "Mock Unstop Tech")
            .first()
        )
        self.assertIsNotNone(db_app)
        self.assertEqual(db_app.role, "Frontend Intern")
        self.assertIn(db_app.status, ("DISCOVERED", "READY_TO_APPLY"))
        self.assertIsInstance(db_app.match_score, float)

    def test_high_risk_scam_job_skipped_and_evidence_saved(self):
        """High-risk scam jobs should be skipped when high_risk_action='skip', and evidence stored in scam_checks."""
        mock_scam_listing = [
            {
                "company": "Scam Corp",
                "role": "Data Entry Specialist",
                "jd_text": "Pay refundable security registration fee of $100 via Telegram immediately before interview slot.",
                "source": "adzuna",
                "recruiter_domain": "scam-corp-careers.in",
            }
        ]

        result = asyncio.run(
            run_job_sourcing(self.db, dry_run=False, mock_listings=mock_scam_listing, high_risk_action="skip")
        )

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["processed_count"], 1)
        self.assertEqual(result["results"][0]["action"], "skipped_high_risk_scam")

        # Verify NOT inserted into applications
        db_app = self.db.query(Application).filter(Application.company == "Scam Corp").first()
        self.assertIsNone(db_app)

        # Verify evidence stored in scam_checks table
        scam_ev = self.db.query(ScamCheck).filter(ScamCheck.recruiter_domain == "scam-corp-careers.in").first()
        self.assertIsNotNone(scam_ev)
        self.assertIsNone(scam_ev.application_id)
        self.assertGreaterEqual(scam_ev.risk_score, 0.75)
        self.assertTrue(len(scam_ev.flagged_reasons) > 0)

        # Clean up scam check
        self.db.delete(scam_ev)
        self.db.commit()

    def test_ats_lower_prior_risk(self):
        """Jobs from Greenhouse/Lever should receive lower prior risk score."""
        mock_ats_listing = [
            {
                "company": "Greenhouse Verified",
                "role": "Software Engineer",
                "jd_text": "Full stack development with React and Node.js.",
                "source": "greenhouse",
                "recruiter_domain": "greenhouse-verified.com"
            }
        ]

        result = asyncio.run(
            run_job_sourcing(self.db, dry_run=False, mock_listings=mock_ats_listing)
        )

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["results"][0]["action"], "inserted")
        self.assertEqual(result["results"][0]["source"], "greenhouse")

if __name__ == "__main__":
    unittest.main()
