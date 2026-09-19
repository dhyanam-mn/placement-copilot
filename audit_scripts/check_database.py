import os
import sys
import json
import sqlalchemy
from sqlalchemy import inspect, text

sys.path.insert(0, os.path.abspath("."))

def audit_database():
    from database import engine
    inspector = inspect(engine)
    
    expected_tables = [
        "applications", "gap_reports", "tailored_resumes", "scam_checks", 
        "profile", "profile_projects", "skills", "resources", "resource_skills", 
        "scam_patterns", "company_watchlist", "settings", "status_events", 
        "notifications", "llm_cache", "gmail_sync_state", "prep_recommendations"
    ]
    
    existing_tables = inspector.get_table_names()
    
    db_report = {
        "tables_summary": {},
        "missing_tables": [],
        "foreign_keys": {},
        "orphan_checks": {},
        "status_distribution": {},
        "status_source_distribution": {},
        "indexes_and_constraints": {},
        "is_demo_column_check": {}
    }
    
    with engine.connect() as conn:
        for t in expected_tables:
            if t in existing_tables:
                columns = [c['name'] for c in inspector.get_columns(t)]
                count = conn.execute(text(f"SELECT COUNT(*) FROM {t};")).scalar()
                db_report["tables_summary"][t] = {
                    "status": "PRESENT",
                    "columns_count": len(columns),
                    "row_count": count,
                    "is_empty": count == 0,
                    "columns": columns
                }
            else:
                db_report["missing_tables"].append(t)
                db_report["tables_summary"][t] = {"status": "MISSING"}
                
        # FK Checks on existing tables
        for t in existing_tables:
            fks = inspector.get_foreign_keys(t)
            db_report["foreign_keys"][t] = fks
            
        # Orphan checks
        # 1. applications.tailored_resume_id -> tailored_resumes.id
        if "applications" in existing_tables and "tailored_resumes" in existing_tables:
            orphans = conn.execute(text(
                "SELECT COUNT(*) FROM applications WHERE tailored_resume_id IS NOT NULL "
                "AND tailored_resume_id NOT IN (SELECT id FROM tailored_resumes);"
            )).scalar()
            db_report["orphan_checks"]["app_tailored_resume_orphans"] = orphans

        # 2. applications.gap_report_id -> gap_reports.id
        if "applications" in existing_tables and "gap_reports" in existing_tables:
            orphans = conn.execute(text(
                "SELECT COUNT(*) FROM applications WHERE gap_report_id IS NOT NULL "
                "AND gap_report_id NOT IN (SELECT id FROM gap_reports);"
            )).scalar()
            db_report["orphan_checks"]["app_gap_report_orphans"] = orphans

        # 3. scam_checks.application_id -> applications.id
        if "scam_checks" in existing_tables:
            orphans = conn.execute(text(
                "SELECT COUNT(*) FROM scam_checks WHERE application_id IS NOT NULL "
                "AND application_id NOT IN (SELECT id FROM applications);"
            )).scalar()
            db_report["orphan_checks"]["scam_check_app_orphans"] = orphans

        # 4. prep_recommendations.application_id -> applications.id
        if "prep_recommendations" in existing_tables:
            orphans = conn.execute(text(
                "SELECT COUNT(*) FROM prep_recommendations WHERE application_id IS NOT NULL "
                "AND application_id NOT IN (SELECT id FROM applications);"
            )).scalar()
            db_report["orphan_checks"]["prep_recommendation_app_orphans"] = orphans

        # Distinct status & status_source in applications
        if "applications" in existing_tables:
            statuses = conn.execute(text("SELECT status, COUNT(*) FROM applications GROUP BY status;")).fetchall()
            db_report["status_distribution"] = {s[0]: s[1] for s in statuses}
            
            sources = conn.execute(text("SELECT status_source, COUNT(*) FROM applications GROUP BY status_source;")).fetchall()
            db_report["status_source_distribution"] = {s[0]: s[1] for s in sources}
            
            cols = [c['name'] for c in inspector.get_columns("applications")]
            db_report["is_demo_column_check"] = {
                "exists": "is_demo" in cols,
                "column_type": str([c['type'] for c in inspector.get_columns("applications") if c['name'] == 'is_demo']) if "is_demo" in cols else None
            }
            
            # Indexes & Unique constraints on applications
            indexes = inspector.get_indexes("applications")
            pk = inspector.get_pk_constraint("applications")
            unique_constraints = inspector.get_unique_constraints("applications")
            db_report["indexes_and_constraints"]["applications"] = {
                "primary_key": pk,
                "indexes": indexes,
                "unique_constraints": unique_constraints
            }

    with open("audit_scripts/database_report.json", "w") as f:
        json.dump(db_report, f, indent=2, default=str)
    
    print(json.dumps(db_report, indent=2, default=str))

if __name__ == "__main__":
    audit_database()
