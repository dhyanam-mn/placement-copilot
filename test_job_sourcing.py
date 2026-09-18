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

from database import SessionLocal
from models import Application
from services.job_sourcing import is_duplicate_application, run_job_sourcing

class TestJobSourcing(unittest.TestCase):

    def setUp(self):
        self.db = SessionLocal()
        # Seed test application in DB
        self.app = Application(
            company="Google Sourcing Test",
            role="Cloud Engineer",
            jd_text="GCP Kubernetes Terraform Python Go",
            source="serpapi",
            status="DISCOVERED",
            match_score=0.82,
        )
        self.db.add(self.app)
        self.db.commit()
        self.db.refresh(self.app)
        self.app_id = self.app.id

    def tearDown(self):
        if hasattr(self, "app_id") and self.app_id:
            to_del = self.db.query(Application).filter(Application.id == self.app_id).first()
            if to_del:
                self.db.delete(to_del)
                self.db.commit()

        # Clean up any created mock items
        created = (
            self.db.query(Application)
            .filter(Application.company.in_(["Mock Amazon Tech", "Mock Unstop Tech"]))
            .all()
        )
        for item in created:
            self.db.delete(item)
        self.db.commit()
        self.db.close()

    def test_deduplication_detects_existing_application(self):
        """is_duplicate_application should return True for existing (company, role, source) tuple."""
        is_dup = is_duplicate_application(
            self.db, company="Google Sourcing Test", role="Cloud Engineer", source="serpapi"
        )
        self.assertTrue(is_dup)

        is_not_dup = is_duplicate_application(
            self.db, company="Google Sourcing Test", role="Frontend Dev", source="serpapi"
        )
        self.assertFalse(is_not_dup)

    def test_dry_run_mode_does_not_insert_rows(self):
        """run_job_sourcing in dry_run=True mode should preview results without writing to DB."""
        mock_listings = [
            {
                "company": "Mock Amazon Tech",
                "role": "SDE-2",
                "jd_text": "Java Distributed Systems AWS SQL DSA",
                "source": "serpapi",
            }
        ]

        count_before = self.db.query(Application).count()

        result = asyncio.run(
            run_job_sourcing(self.db, dry_run=True, mock_listings=mock_listings)
        )

        count_after = self.db.query(Application).count()
        self.assertEqual(count_before, count_after)
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
                "source": "serpapi",
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
        self.assertEqual(db_app.status, "DISCOVERED")
        self.assertIsInstance(db_app.match_score, float)

if __name__ == "__main__":
    unittest.main()
