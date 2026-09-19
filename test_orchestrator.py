import unittest
import asyncio
from datetime import datetime, timezone
from database import SessionLocal
from models import Application, TailoredResume, GapReport, PrepRecommendation
from services.orchestrator import (
    run_application_workflow,
    confirm_application_applied,
    orchestrator_graph,
)


class TestOrchestrator(unittest.TestCase):
    def setUp(self):
        self.db = SessionLocal()
        self.created_apps = []
        from sqlalchemy import text
        self.db.execute(text("UPDATE applications SET tailored_resume_id = NULL, gap_report_id = NULL WHERE company IN ('Orchestrator Safe Co', 'Scam Tech Corp', 'Resume Co');"))
        self.db.execute(text("DELETE FROM applications WHERE company IN ('Orchestrator Safe Co', 'Scam Tech Corp', 'Resume Co');"))
        self.db.commit()

    def tearDown(self):
        from sqlalchemy import text
        try:
            self.db.execute(text("UPDATE applications SET tailored_resume_id = NULL, gap_report_id = NULL WHERE company IN ('Orchestrator Safe Co', 'Scam Tech Corp', 'Resume Co');"))
            self.db.execute(text("DELETE FROM applications WHERE company IN ('Orchestrator Safe Co', 'Scam Tech Corp', 'Resume Co');"))
            self.db.commit()
        except Exception:
            self.db.rollback()
        finally:
            self.db.close()

    def test_workflow_initial_run_pauses_at_ready_to_apply(self):
        """Workflow should run scout -> scam_check -> tailoring and pause at READY_TO_APPLY checkpoint."""
        app = Application(
            company="Orchestrator Safe Co",
            role="Python Developer",
            jd_text="Experience with Python, FastAPI, and PostgreSQL required.",
            source="adzuna",
            status="DISCOVERED",
        )
        self.db.add(app)
        self.db.commit()
        self.db.refresh(app)
        self.created_apps.append(app)

        res_state = asyncio.run(run_application_workflow(self.db, app))
        self.db.refresh(app)

        self.assertEqual(app.status, "READY_TO_APPLY")
        self.assertIsNotNone(app.tailored_resume_id)

    def test_workflow_scam_check_branching_flagged_scam(self):
        """Workflow should set status to FLAGGED_SCAM if risk score >= 0.7."""
        app = Application(
            company="Scam Tech Corp",
            role="Data Entry",
            jd_text="Contact recruiter@scamtech-jobs.com. Earn $500/hr from home! Wire transfer $100 processing fee via telegram before interview.",
            source="adzuna",
            status="DISCOVERED",
        )
        self.db.add(app)
        self.db.commit()
        self.db.refresh(app)
        self.created_apps.append(app)

        res_state = asyncio.run(run_application_workflow(self.db, app))
        self.db.refresh(app)

        self.assertEqual(app.status, "REJECTED")
        self.assertEqual(res_state.get("status"), "FLAGGED_SCAM")
        self.assertGreaterEqual(res_state.get("risk_score", 0.0), 0.7)

    def test_confirm_applied_resumes_workflow_past_checkpoint(self):
        """Confirming applied should set status to APPLIED and advance graph past checkpoint."""
        app = Application(
            company="Resume Co",
            role="Full Stack Engineer",
            jd_text="Python, Docker, and React skills required.",
            source="adzuna",
            status="DISCOVERED",
        )
        self.db.add(app)
        self.db.commit()
        self.db.refresh(app)
        self.created_apps.append(app)

        # Run initial workflow -> pauses at READY_TO_APPLY
        asyncio.run(run_application_workflow(self.db, app))
        self.db.refresh(app)
        self.assertEqual(app.status, "READY_TO_APPLY")

        # Confirm submission via confirm_application_applied
        asyncio.run(confirm_application_applied(self.db, app.id))
        self.db.refresh(app)

        self.assertEqual(app.status, "APPLIED")
        self.assertEqual(app.status_source, "manual")


if __name__ == "__main__":
    unittest.main()
