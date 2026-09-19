import unittest
import json
import hashlib
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base, SessionLocal
from models import Application, Skill, Resource, ResourceSkill, PrepRecommendation, LLMCache, ProfileProject
from services.prep_agent import (
    extract_jd_skills,
    get_profile_skills,
    rank_resources_sql,
    validate_and_parse_llm_json,
    generate_prep_recommendations,
    get_application_prep_recommendations,
    _get_cached_llm_response,
    _save_llm_cache,
)


class TestPrepAgent(unittest.TestCase):
    def setUp(self):
        self.db = SessionLocal()
        # Clean up any leftover test data
        self.db.query(ResourceSkill).filter(ResourceSkill.skill_name.like("%TestSkill")).delete(synchronize_session=False)
        self.db.query(Skill).filter(Skill.name.like("%TestSkill")).delete(synchronize_session=False)
        self.db.query(Resource).filter(Resource.title.like("% Test Doc")).delete(synchronize_session=False)
        self.db.commit()

        # Seed test data
        s1 = Skill(name="PythonTestSkill", aliases=["pytestskill", "python3test"])
        s2 = Skill(name="DockerTestSkill", aliases=["dockertestskill", "containerstest"])
        s3 = Skill(name="PostgreSQLTestSkill", aliases=["postgrestest", "psqltest"])
        s4 = Skill(name="PyTorchTestSkill", aliases=["torchtest"])
        self.db.add_all([s1, s2, s3, s4])

        r1 = Resource(title="Python Test Doc", url="https://docs.python.org/3/", is_active=True)
        r2 = Resource(title="Docker Test Doc", url="https://docs.docker.com/", is_active=True)
        r3 = Resource(title="PostgreSQL Test Doc", url="https://www.postgresql.org/docs/", is_active=True)
        r4 = Resource(title="PyTorch Test Doc", url="https://pytorch.org/tutorials/", is_active=True)
        self.db.add_all([r1, r2, r3, r4])
        self.db.commit()

        rs1 = ResourceSkill(resource_id=r1.id, skill_name="PythonTestSkill", weight=1.0)
        rs2 = ResourceSkill(resource_id=r2.id, skill_name="DockerTestSkill", weight=1.0)
        rs3 = ResourceSkill(resource_id=r3.id, skill_name="PostgreSQLTestSkill", weight=1.0)
        rs4 = ResourceSkill(resource_id=r4.id, skill_name="PyTorchTestSkill", weight=1.0)
        self.db.add_all([rs1, rs2, rs3, rs4])
        self.db.commit()

        self.r1 = r1
        self.r2 = r2
        self.r3 = r3
        self.r4 = r4
        self.created_skills = [s1, s2, s3, s4]
        self.created_resources = [r1, r2, r3, r4]

    def tearDown(self):
        try:
            self.db.query(ResourceSkill).filter(ResourceSkill.skill_name.like("%TestSkill")).delete(synchronize_session=False)
            for a in getattr(self, "created_apps", []):
                self.db.query(PrepRecommendation).filter(PrepRecommendation.application_id == a.id).delete(synchronize_session=False)
                self.db.query(Application).filter(Application.id == a.id).delete(synchronize_session=False)
            for r in getattr(self, "created_resources", []):
                self.db.query(PrepRecommendation).filter(PrepRecommendation.resource_id == r.id).delete(synchronize_session=False)
                self.db.query(Resource).filter(Resource.id == r.id).delete(synchronize_session=False)
            for s in getattr(self, "created_skills", []):
                self.db.query(Skill).filter(Skill.id == s.id).delete(synchronize_session=False)
            self.db.commit()
        except Exception:
            self.db.rollback()
        finally:
            self.db.close()

    def test_extract_jd_skills(self):
        jd_text = "We are seeking a Backend Engineer skilled in pytestskill, containerstest, and postgrestest databases."
        extracted = extract_jd_skills(self.db, jd_text)
        self.assertIn("PythonTestSkill", extracted)
        self.assertIn("DockerTestSkill", extracted)
        self.assertIn("PostgreSQLTestSkill", extracted)
        self.assertNotIn("PyTorchTestSkill", extracted)

    def test_rank_resources_sql_gap_weighting(self):
        jd_skills = ["PythonTestSkill", "DockerTestSkill", "PostgreSQLTestSkill"]
        gap_skills = {"DockerTestSkill", "PostgreSQLTestSkill"}
        profile_skills = {"PythonTestSkill"}

        candidates = rank_resources_sql(self.db, jd_skills, gap_skills, profile_skills, limit=10)
        candidate_ids = [c["id"] for c in candidates]

        # Verify candidate resources matched the gap skills
        self.assertIn(self.r2.id, candidate_ids)
        self.assertIn(self.r3.id, candidate_ids)
        # r2 (gap skill) should rank before r1 (matched non-gap skill)
        r2_index = candidate_ids.index(self.r2.id)
        r1_index = candidate_ids.index(self.r1.id)
        self.assertLess(r2_index, r1_index)

    def test_validate_and_parse_llm_json(self):
        valid_ids = {self.r1.id, self.r2.id}
        llm_json = json.dumps([
            {"resource_id": self.r1.id, "reason": "Master core Python syntax", "est_hours": 4},
            {"resource_id": 9999, "reason": "Unknown resource should be dropped", "est_hours": 2},
            {"resource_id": self.r2.id, "reason": "Dockerize microservices", "est_hours": 5},
        ])

        parsed = validate_and_parse_llm_json(llm_json, valid_ids, max_items=5)
        self.assertEqual(len(parsed), 2)
        parsed_ids = [p["resource_id"] for p in parsed]
        self.assertIn(self.r1.id, parsed_ids)
        self.assertIn(self.r2.id, parsed_ids)
        self.assertNotIn(9999, parsed_ids)

    def test_llm_cache_saving_and_retrieval(self):
        unique_key = f"test_prompt_{datetime.now(timezone.utc).timestamp()}"
        prompt_hash = hashlib.sha256(unique_key.encode("utf-8")).hexdigest()
        response_text = json.dumps([{"resource_id": 1, "reason": "Cached recommendation", "est_hours": 2}])

        # Verify not cached initially
        self.assertIsNone(_get_cached_llm_response(self.db, prompt_hash))

        # Save to cache
        _save_llm_cache(self.db, prompt_hash, response_text)

        # Verify retrieval
        cached = _get_cached_llm_response(self.db, prompt_hash)
        self.assertEqual(cached, response_text)

        # Clean up
        self.db.query(LLMCache).filter(LLMCache.prompt_hash == prompt_hash).delete(synchronize_session=False)
        self.db.commit()

    def test_get_application_prep_recommendations_resolves_urls_strictly_by_id(self):
        app = Application(
            company="Test Co",
            role="Backend Dev",
            jd_text="Python and Docker engineer required.",
            source="adzuna",
            status="INTERVIEW",
        )
        self.db.add(app)
        self.db.commit()
        self.created_apps = [app]

        rec = PrepRecommendation(
            application_id=app.id,
            resource_id=self.r1.id,
            reason="Master Python fundamentals",
            est_hours=3,
        )
        self.db.add(rec)
        self.db.commit()

        results = get_application_prep_recommendations(self.db, app.id)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["resource_id"], self.r1.id)
        self.assertEqual(results[0]["title"], "Python Test Doc")
        self.assertEqual(results[0]["url"], "https://docs.python.org/3/")


if __name__ == "__main__":
    unittest.main()
