import os
import sys
import json
import argparse
import logging
from typing import Any, List, Dict, Optional
from datetime import datetime, timezone, timedelta

# Add root directory to sys.path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, root_dir)

from database import SessionLocal
from models import (
    Skill,
    Resource,
    ResourceSkill,
    ScamPattern,
    CompanyWatchlist,
    Setting,
    Profile,
    ProfileProject,
    Application,
    TailoredResume,
    GapReport,
    ScamCheck,
    Notification,
    PrepRecommendation,
    StatusEvent,
)

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger("placement_copilot.seed")

SEEDS_DIR = os.path.join(root_dir, "db", "seeds")


def load_seed_json(filename: str) -> Any:
    filepath = os.path.join(SEEDS_DIR, filename)
    if not os.path.exists(filepath):
        logger.warning(f"Seed file '{filename}' not found at {filepath}.")
        return []
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def reset_demo_data(db):
    """
    Purges ONLY records flagged with is_demo=True across all database tables.
    Real pipeline records (is_demo=False) are preserved intact.
    """
    logger.info("Resetting demo data (purging records with is_demo=True)...")

    # Clear foreign keys on applications
    db.query(Application).filter(Application.is_demo == True).update(
        {"gap_report_id": None, "tailored_resume_id": None}, synchronize_session=False
    )
    db.commit()

    # Delete child tables referencing applications
    db.query(PrepRecommendation).filter(PrepRecommendation.is_demo == True).delete(synchronize_session=False)
    db.query(StatusEvent).filter(StatusEvent.is_demo == True).delete(synchronize_session=False)
    db.query(Notification).filter(Notification.is_demo == True).delete(synchronize_session=False)
    db.query(ScamCheck).filter(ScamCheck.is_demo == True).delete(synchronize_session=False)
    db.commit()

    # Delete demo applications
    db.query(Application).filter(Application.is_demo == True).delete(synchronize_session=False)
    db.commit()

    # Delete gap reports & tailored resumes
    db.query(GapReport).filter(GapReport.is_demo == True).delete(synchronize_session=False)
    db.query(TailoredResume).filter(TailoredResume.is_demo == True).delete(synchronize_session=False)
    db.commit()

    # Resource skills for demo resources
    demo_resource_ids = [r.id for r in db.query(Resource).filter(Resource.is_demo == True).all()]
    if demo_resource_ids:
        db.query(ResourceSkill).filter(ResourceSkill.resource_id.in_(demo_resource_ids)).delete(synchronize_session=False)

    # Resources, Skills, ScamPatterns, Watchlist, Profile, ProfileProjects
    db.query(Resource).filter(Resource.is_demo == True).delete(synchronize_session=False)
    db.query(Skill).filter(Skill.is_demo == True).delete(synchronize_session=False)
    db.query(ScamPattern).filter(ScamPattern.is_demo == True).delete(synchronize_session=False)
    db.query(CompanyWatchlist).filter(CompanyWatchlist.is_demo == True).delete(synchronize_session=False)
    db.query(ProfileProject).filter(ProfileProject.is_demo == True).delete(synchronize_session=False)
    db.query(Profile).filter(Profile.is_demo == True).delete(synchronize_session=False)

    db.commit()
    logger.info("Successfully reset demo data.")


def seed_demo_data(db):
    """
    Idempotent seeding function: resets existing demo records, then populates
    skills, resources, scam patterns, watchlist, settings, demo profile, and demo applications.
    """
    # Clean previous demo records for idempotency
    reset_demo_data(db)

    logger.info("Seeding domain data and demo applications...")

    # 1. Seed Skills
    skills_data = load_seed_json("skills.json")
    skill_map = {}
    for item in skills_data:
        existing = db.query(Skill).filter(Skill.name == item["name"]).first()
        if not existing:
            skill_obj = Skill(
                name=item["name"],
                category=item.get("category"),
                aliases=item.get("aliases", []),
                is_demo=True,
            )
            db.add(skill_obj)
            db.commit()
            db.refresh(skill_obj)
            skill_map[item["name"]] = skill_obj
        else:
            skill_map[item["name"]] = existing

    # 2. Seed Resources & ResourceSkills
    resources_data = load_seed_json("resources.json")
    for item in resources_data:
        existing = db.query(Resource).filter(Resource.title == item["title"]).first()
        if not existing:
            res_obj = Resource(
                title=item["title"],
                url=item["url"],
                is_active=item.get("is_active", True),
                verified_at=datetime.now(timezone.utc),
                is_demo=True,
            )
            db.add(res_obj)
            db.commit()
            db.refresh(res_obj)

            for s_name in item.get("skills", []):
                if s_name in skill_map:
                    rs = ResourceSkill(resource_id=res_obj.id, skill_name=s_name, weight=1.0)
                    db.add(rs)
            db.commit()

    # 3. Seed Scam Patterns
    scam_patterns_data = load_seed_json("scam_patterns.json")
    for item in scam_patterns_data:
        existing = db.query(ScamPattern).filter(ScamPattern.pattern == item["pattern"]).first()
        if not existing:
            sp = ScamPattern(
                category=item["category"],
                pattern=item["pattern"],
                weight=item["weight"],
                source_note=item.get("source_note", "Demo seed"),
                is_demo=True,
            )
            db.add(sp)
    db.commit()

    # 4. Seed Watchlist
    watchlist_data = load_seed_json("watchlist.json")
    for item in watchlist_data:
        existing = db.query(CompanyWatchlist).filter(CompanyWatchlist.company == item["company"]).first()
        if not existing:
            cw = CompanyWatchlist(
                company=item["company"],
                ats=item.get("ats"),
                token=item.get("token"),
                active=item.get("active", True),
                is_demo=True,
            )
            db.add(cw)
    db.commit()

    # 5. Seed Settings
    settings_data = load_seed_json("settings.json")
    for item in settings_data:
        setting = db.query(Setting).filter(Setting.key == item["key"]).first()
        if not setting:
            setting = Setting(key=item["key"], value=item["value"])
            db.add(setting)
        else:
            setting.value = item["value"]
    db.commit()

    # 6. Seed Demo Profile & Projects
    profile_data = load_seed_json("demo_profile.json")
    if profile_data:
        prof = Profile(
            name=profile_data.get("name", "Demo Candidate"),
            email=profile_data.get("email", "candidate@demo.ai"),
            contact_info=profile_data.get("contact_info", "+1-555-0199"),
            is_demo=True,
        )
        db.add(prof)
        db.commit()
        db.refresh(prof)

        for proj in profile_data.get("projects", []):
            pp = ProfileProject(
                profile_id=prof.id,
                project_name=proj["project_name"],
                bullet_text=proj["bullet_text"],
                skill_tags=proj.get("skill_tags", []),
                is_demo=True,
            )
            db.add(pp)
        db.commit()

    # 7. Seed ~12 Demo Applications with backdated last_contact_date
    apps_data = load_seed_json("demo_applications.json")
    now_utc = datetime.now(timezone.utc)

    for item in apps_data:
        days_ago = item.get("last_contact_days_ago", 0)
        contact_date = now_utc - timedelta(days=days_ago)

        app_obj = Application(
            company=item["company"],
            role=item["role"],
            jd_text=item["jd_text"],
            source=item["source"],
            status=item["status"],
            status_source=item.get("status_source", "manual"),
            match_score=0.85,
            last_contact_date=contact_date,
            last_updated=contact_date,
            created_at=contact_date,
            is_demo=True,
        )
        db.add(app_obj)
        db.commit()
        db.refresh(app_obj)

        # Seed related outputs for demo rows based on status
        if item["status"] in ("REJECTED", "GHOSTED"):
            gap = GapReport(
                application_id=app_obj.id,
                report_type="per_row",
                summary_text=f"Application for '{app_obj.company}' ({app_obj.role}) ended in {item['status']}.",
                details={"missing_skills": ["System Design", "Kubernetes"], "matched_skills": ["Python", "FastAPI"]},
                is_demo=True,
            )
            db.add(gap)
            db.commit()
            db.refresh(gap)
            app_obj.gap_report_id = gap.id
            db.commit()

        if item["company"] == "Fake Tech Scam":
            scam = ScamCheck(
                application_id=app_obj.id,
                recruiter_name="Fake Recruiter",
                recruiter_domain="scamtech-jobs.com",
                risk_score=0.9,
                flagged_reasons=["Lookalike domain '-jobs'", "Demands $100 processing fee"],
                explanation_text="This recruiter outreach was flagged due to suspicious domain and payment demand.",
                is_demo=True,
            )
            db.add(scam)
            db.commit()

        if item["status"] == "INTERVIEW":
            # Link a sample resource recommendation
            res_first = db.query(Resource).first()
            if res_first:
                rec = PrepRecommendation(
                    application_id=app_obj.id,
                    resource_id=res_first.id,
                    reason="Recommended resource to prepare for your technical interview.",
                    est_hours=3,
                    is_demo=True,
                )
                db.add(rec)
                db.commit()

    logger.info(f"Seeding completed successfully! Inserted {len(apps_data)} demo applications with is_demo=True.")


def main():
    parser = argparse.ArgumentParser(description="Idempotent seed script for Placement Copilot database.")
    parser.add_argument("--demo", action="store_true", help="Seed domain data and demo applications (default action)")
    parser.add_argument("--reset-demo", action="store_true", help="Purge all records with is_demo=True")

    args = parser.parse_args()
    db = SessionLocal()

    try:
        if args.reset_demo:
            reset_demo_data(db)
        else:
            # Default to demo seeding if no args or --demo provided
            seed_demo_data(db)
    except Exception as exc:
        logger.error(f"Error during seeding: {exc}", exc_info=True)
        db.rollback()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
