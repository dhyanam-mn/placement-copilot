import sys
import os
import unittest
import asyncio
from datetime import datetime, timezone, timedelta

# Ensure root workspace is preferred in sys.path over model-service
root_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, root_dir)

# Unload any previously cached 'schemas' module (e.g. from model-service/schemas.py)
if "schemas" in sys.modules and not hasattr(sys.modules["schemas"], "ApplicationStatusPatchRequest"):
    del sys.modules["schemas"]

from database import SessionLocal
from models import Application
from schemas import ApplicationStatusPatchRequest
from routers.applications import update_application_status

class TestApplicationStatusUpdate(unittest.TestCase):

    def setUp(self):
        self.db = SessionLocal()
        # Create a test application row with an old last_contact_date
        old_date = datetime.now(timezone.utc) - timedelta(days=10)
        self.test_app = Application(
            company="Test Company",
            role="Software Engineer",
            jd_text="Python FastAPI PostgreSQL",
            source="serpapi",
            status="APPLIED",
            status_source="manual",
            match_score=0.8,
            last_contact_date=old_date
        )
        self.db.add(self.test_app)
        self.db.commit()
        self.db.refresh(self.test_app)
        self.app_id = self.test_app.id

    def tearDown(self):
        # Cleanup created test row
        if hasattr(self, 'app_id') and self.app_id:
            app_to_delete = self.db.query(Application).filter(Application.id == self.app_id).first()
            if app_to_delete:
                self.db.delete(app_to_delete)
                self.db.commit()
        self.db.close()

    def test_manual_status_update_changes_last_contact_date(self):
        """PATCH with status_source='manual' MUST update last_contact_date to now()."""
        initial_contact_date = self.test_app.last_contact_date

        payload = ApplicationStatusPatchRequest(status="INTERVIEW", status_source="manual")
        updated_app = asyncio.run(update_application_status(self.app_id, payload, self.db))

        self.assertEqual(updated_app.status, "INTERVIEW")
        self.assertEqual(updated_app.status_source, "manual")

        # Verify last_contact_date changed and is updated to a more recent time
        self.assertGreater(updated_app.last_contact_date, initial_contact_date)

    def test_auto_ghost_status_update_preserves_last_contact_date(self):
        """PATCH with status_source='auto_ghost' MUST NOT update last_contact_date, but last_updated changes."""
        # First update with manual to establish a known baseline last_contact_date
        manual_payload = ApplicationStatusPatchRequest(status="APPLIED", status_source="manual")
        baseline_app = asyncio.run(update_application_status(self.app_id, manual_payload, self.db))
        baseline_contact_date = baseline_app.last_contact_date

        # Perform auto_ghost update
        ghost_payload = ApplicationStatusPatchRequest(status="GHOSTED", status_source="auto_ghost")
        ghost_app = asyncio.run(update_application_status(self.app_id, ghost_payload, self.db))

        self.assertEqual(ghost_app.status, "GHOSTED")
        self.assertEqual(ghost_app.status_source, "auto_ghost")
        # Confirm last_contact_date was NOT touched
        self.assertEqual(ghost_app.last_contact_date, baseline_contact_date)

    def test_gmail_auto_status_update_changes_last_contact_date(self):
        """PATCH with status_source='gmail_auto' MUST update last_contact_date as a real signal."""
        initial_contact_date = self.test_app.last_contact_date

        payload = ApplicationStatusPatchRequest(status="OA_INVITE", status_source="gmail_auto")
        updated_app = asyncio.run(update_application_status(self.app_id, payload, self.db))

        self.assertEqual(updated_app.status, "OA_INVITE")
        self.assertEqual(updated_app.status_source, "gmail_auto")
        self.assertGreater(updated_app.last_contact_date, initial_contact_date)

if __name__ == "__main__":
    unittest.main()
