import unittest
import json
from fastapi.testclient import TestClient
from sqlalchemy import text

from main import app
from database import SessionLocal
from models import (
    Application,
    Notification,
    StatusEvent,
    ScamCheck,
    Profile,
    ProfileProject,
    Resource,
    Skill,
    ScamPattern,
    CompanyWatchlist,
    Setting,
)


class TestNewEndpoints(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.db = SessionLocal()
        # Clean up test rows if left over
        self.db.query(Resource).filter(Resource.title.like("%GraphQL%")).delete(synchronize_session=False)
        self.db.query(Skill).filter(Skill.name == "TestGraphQL").delete(synchronize_session=False)
        self.db.query(ScamPattern).filter(ScamPattern.pattern == "buy crypto test").delete(synchronize_session=False)
        self.db.query(CompanyWatchlist).filter(CompanyWatchlist.company == "TestWatchCompany").delete(synchronize_session=False)
        self.db.query(Setting).filter(Setting.key == "test_setting_key").delete(synchronize_session=False)
        self.db.commit()

    def tearDown(self):
        self.db.query(Resource).filter(Resource.title.like("%GraphQL%")).delete(synchronize_session=False)
        self.db.query(Skill).filter(Skill.name == "TestGraphQL").delete(synchronize_session=False)
        self.db.query(ScamPattern).filter(ScamPattern.pattern == "buy crypto test").delete(synchronize_session=False)
        self.db.query(CompanyWatchlist).filter(CompanyWatchlist.company == "TestWatchCompany").delete(synchronize_session=False)
        self.db.query(Setting).filter(Setting.key == "test_setting_key").delete(synchronize_session=False)
        self.db.commit()
        self.db.close()

    def test_cors_headers_and_preflight(self):
        """Verify CORS headers respond correctly on preflight OPTIONS requests."""
        response = self.client.options(
            "/applications",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("access-control-allow-origin", response.headers)

    def test_health_endpoint(self):
        """GET /health should return detailed service health statuses."""
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("status", data)
        self.assertIn("services", data)
        self.assertIn("postgres", data["services"])
        self.assertEqual(data["services"]["postgres"], "healthy")

    def test_notifications_endpoints(self):
        """GET /notifications and POST /notifications/{id}/read."""
        # Create test notification
        notif = Notification(type="test_alert", content="Test Notification Content", read=False)
        self.db.add(notif)
        self.db.commit()

        # Unread filter
        res_unread = self.client.get("/notifications?unread_only=true")
        self.assertEqual(res_unread.status_code, 200)
        unread_list = res_unread.json()["notifications"]
        self.assertTrue(any(n["id"] == notif.id for n in unread_list))

        # Mark as read
        res_read = self.client.post(f"/notifications/{notif.id}/read")
        self.assertEqual(res_read.status_code, 200)
        self.assertTrue(res_read.json()["read"])

        # Clean up
        self.db.delete(notif)
        self.db.commit()

    def test_applications_filtering_events_and_scam_check(self):
        """Test GET /applications?status=&source=&is_demo=, /events, and /scam-check."""
        app_obj = Application(
            company="Filter & Event Corp",
            role="Systems Engineer",
            jd_text="Python and C++ required.",
            source="adzuna",
            status="DISCOVERED",
            is_demo=True,
        )
        self.db.add(app_obj)
        self.db.commit()

        # 1. Filtering
        res_filter = self.client.get("/applications?source=adzuna&is_demo=true")
        self.assertEqual(res_filter.status_code, 200)
        apps = res_filter.json()["applications"]
        self.assertTrue(any(a["id"] == app_obj.id for a in apps))

        # 2. Events
        event = StatusEvent(
            application_id=app_obj.id,
            old_status="DISCOVERED",
            new_status="READY_TO_APPLY",
            event_source="manual",
        )
        self.db.add(event)
        self.db.commit()

        res_events = self.client.get(f"/applications/{app_obj.id}/events")
        self.assertEqual(res_events.status_code, 200)
        events_list = res_events.json()["events"]
        self.assertEqual(len(events_list), 1)
        self.assertEqual(events_list[0]["new_status"], "READY_TO_APPLY")

        # 3. Scam check GET
        scam = ScamCheck(
            application_id=app_obj.id,
            recruiter_name="Fake Recruiter",
            recruiter_domain="fakecorp.net",
            risk_score=0.95,
            flagged_reasons=["Lookalike domain", "Telegram outreach"],
            explanation_text="Obvious scam outreach.",
        )
        self.db.add(scam)
        self.db.commit()

        res_scam = self.client.get(f"/applications/{app_obj.id}/scam-check")
        self.assertEqual(res_scam.status_code, 200)
        scam_data = res_scam.json()
        self.assertEqual(scam_data["risk_score"], 0.95)
        self.assertIn("Lookalike domain", scam_data["flagged_reasons"])

        # Clean up
        self.db.delete(scam)
        self.db.delete(event)
        self.db.delete(app_obj)
        self.db.commit()

    def test_profile_crud_and_import(self):
        """CRUD for /profile and /profile/projects, plus POST /profile/import."""
        # 1. Update Profile
        res_prof = self.client.post(
            "/profile",
            json={"name": "Alice Developer", "email": "alice@example.com", "contact_info": "+1234567890"},
        )
        self.assertEqual(res_prof.status_code, 201)
        self.assertEqual(res_prof.json()["name"], "Alice Developer")

        # 2. Create Project
        res_proj = self.client.post(
            "/profile/projects",
            json={"project_name": "Antigravity Pipeline", "bullet_text": "Built agentic system", "skill_tags": ["Python", "FastAPI"]},
        )
        self.assertEqual(res_proj.status_code, 201)
        proj_id = res_proj.json()["id"]

        # 3. Import JSON Profile
        import_payload = {
            "name": "Bob Senior Dev",
            "email": "bob@example.com",
            "projects": [
                {
                    "project_name": "Imported Microservice",
                    "bullet_text": "Architected distributed service",
                    "skill_tags": ["Go", "Docker"],
                }
            ],
        }
        res_imp = self.client.post("/profile/import", json=import_payload)
        self.assertEqual(res_imp.status_code, 200)
        imp_data = res_imp.json()
        self.assertEqual(imp_data["name"], "Bob Senior Dev")
        self.assertEqual(len(imp_data["projects"]), 1)
        self.assertEqual(imp_data["projects"][0]["project_name"], "Imported Microservice")

    def test_entity_cruds(self):
        """CRUD endpoints for /resources, /skills, /scam-patterns, /watchlist, /settings."""
        # 1. Skills CRUD
        res_skill = self.client.post("/skills", json={"name": "TestGraphQL", "category": "API", "aliases": ["gql"]})
        self.assertEqual(res_skill.status_code, 201)
        skill_id = res_skill.json()["id"]

        # 2. Resources CRUD
        res_res = self.client.post(
            "/resources",
            json={
                "title": "GraphQL Official Docs",
                "url": "https://graphql.org/learn/",
                "is_active": True,
                "skills": [{"skill_name": "TestGraphQL", "weight": 1.0}],
            },
        )
        self.assertEqual(res_res.status_code, 201)
        res_id = res_res.json()["id"]

        # 3. Scam Patterns CRUD
        res_pat = self.client.post(
            "/scam-patterns",
            json={"category": "payment_demand", "pattern": "buy crypto test", "weight": 0.8, "source_note": "Unit Test"},
        )
        self.assertEqual(res_pat.status_code, 201)
        pat_id = res_pat.json()["id"]

        # 4. Watchlist CRUD
        res_watch = self.client.post(
            "/watchlist",
            json={"company": "TestWatchCompany", "ats": "greenhouse", "token": "testtoken", "active": True},
        )
        self.assertEqual(res_watch.status_code, 201)
        watch_id = res_watch.json()["id"]

        # 5. Settings CRUD
        res_set = self.client.post("/settings", json={"key": "test_setting_key", "value": 42})
        self.assertEqual(res_set.status_code, 201)

        # Cleanup
        self.client.delete(f"/resources/{res_id}")
        self.client.delete(f"/skills/{skill_id}")
        self.client.delete(f"/scam-patterns/{pat_id}")
        self.client.delete(f"/watchlist/{watch_id}")


if __name__ == "__main__":
    unittest.main()
