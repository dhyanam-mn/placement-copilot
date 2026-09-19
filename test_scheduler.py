import unittest
import asyncio
from fastapi.testclient import TestClient
from main import app
from services.scheduler import (
    start_scheduler,
    shutdown_scheduler,
    get_scheduled_jobs_status,
    trigger_job_by_id,
)


class TestScheduler(unittest.TestCase):
    def test_scheduled_jobs_status(self):
        """Scheduler should register scout_sync, gmail_sync_auto_ghost, and gap_aggregate jobs."""
        with TestClient(app):
            jobs = get_scheduled_jobs_status()
            job_ids = [j["id"] for j in jobs]

            self.assertIn("scout_sync", job_ids)
            self.assertIn("gmail_sync_auto_ghost", job_ids)
            self.assertIn("gap_aggregate", job_ids)

    def test_trigger_job_by_id(self):
        """Manual trigger helper should execute specified background job."""
        res = asyncio.run(trigger_job_by_id("scout_sync"))
        self.assertEqual(res["status"], "triggered")
        self.assertEqual(res["job_id"], "scout_sync")

    def test_scheduler_admin_endpoints(self):
        """FastAPI admin endpoints should list and trigger scheduled jobs."""
        with TestClient(app) as client:
            res_list = client.get("/admin/scheduler/jobs")
            self.assertEqual(res_list.status_code, 200)
            jobs = res_list.json()
            self.assertGreaterEqual(len(jobs), 3)

            res_trig = client.post("/admin/scheduler/scout_sync/trigger")
            self.assertEqual(res_trig.status_code, 200)
            data = res_trig.json()
            self.assertEqual(data["status"], "triggered")


if __name__ == "__main__":
    unittest.main()
