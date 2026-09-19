import os
import sys
import json

sys.path.insert(0, os.path.abspath("."))

from database import SessionLocal
from sqlalchemy import text
from services.gmail_tracker import match_email_to_application

def run_queries():
    db = SessionLocal()
    report = {}
    
    # Q1: Auto-ghost ghosted applications in last 24h
    ghosted_query = text("""
        SELECT id, company, role, source, status, status_source, last_contact_date, last_updated, is_demo, gap_report_id
        FROM applications 
        WHERE status = 'GHOSTED' AND last_updated >= NOW() - INTERVAL '24 hours'
        ORDER BY id ASC;
    """)
    ghosted_rows = [dict(r._mapping) for r in db.execute(ghosted_query).fetchall()]
    report["q1_ghosted_rows"] = ghosted_rows
    
    # Check gap report & notification for second ghosted row if exists
    if len(ghosted_rows) >= 2:
        second_row = ghosted_rows[1]
        second_id = second_row["id"]
        gap_rep = db.execute(text("SELECT id, summary_text FROM gap_reports WHERE application_id = :id;"), {"id": second_id}).fetchone()
        notifs = db.execute(text("SELECT id, type, content FROM notifications WHERE content LIKE :pattern;"), {"pattern": f"%{second_row['company']}%"}).fetchall()
        report["q1_second_row_details"] = {
            "row": second_row,
            "gap_report": dict(gap_rep._mapping) if gap_rep else None,
            "notifications": [dict(n._mapping) for n in notifs]
        }
    else:
        report["q1_second_row_details"] = None

    # Q2: Row counts split by is_demo and source; duplicate (company, role, source)
    split_query = text("""
        SELECT is_demo, source, COUNT(*) 
        FROM applications 
        GROUP BY is_demo, source 
        ORDER BY is_demo, source;
    """)
    splits = [dict(r._mapping) for r in db.execute(split_query).fetchall()]
    report["q2_splits"] = splits
    
    dupes_query = text("""
        SELECT company, role, source, COUNT(*) as cnt
        FROM applications
        GROUP BY company, role, source
        HAVING COUNT(*) > 1
        ORDER BY cnt DESC;
    """)
    dupes = [dict(r._mapping) for r in db.execute(dupes_query).fetchall()]
    report["q2_duplicates"] = dupes
    
    total_count = db.execute(text("SELECT COUNT(*) FROM applications;")).scalar()
    report["q2_total_rows"] = total_count

    # Q7: Resources per skill and skills with zero resources
    res_per_skill_query = text("""
        SELECT s.name AS skill_name, COUNT(rs.resource_id) AS resource_count
        FROM skills s
        LEFT JOIN resource_skills rs ON LOWER(s.name) = LOWER(rs.skill_name)
        GROUP BY s.name
        ORDER BY resource_count DESC, s.name ASC;
    """)
    res_per_skill = [dict(r._mapping) for r in db.execute(res_per_skill_query).fetchall()]
    zero_res_skills = [s["skill_name"] for s in res_per_skill if s["resource_count"] == 0]
    
    report["q7_resources_per_skill"] = res_per_skill
    report["q7_zero_resource_skills_count"] = len(zero_res_skills)
    report["q7_zero_resource_skills"] = zero_res_skills

    db.close()
    
    with open("audit_scripts/questions_report.json", "w") as f:
        json.dump(report, f, indent=2, default=str)
        
    print(json.dumps(report, indent=2, default=str))

if __name__ == "__main__":
    run_queries()
