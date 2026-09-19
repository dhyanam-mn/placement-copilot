import os
import sys
import json

sys.path.insert(0, os.path.abspath("."))

def inspect_db_usage():
    report = {}
    
    # Check scam_check.py DB reading
    with open("services/scam_check.py", "r", encoding="utf-8") as f:
        scam_code = f.read()
    report["scam_check_db_read"] = "scam_patterns" in scam_code and "db.query" in scam_code or "select" in scam_code.lower()
    
    # Check gmail_tracker.py DB reading for state & settings
    with open("services/gmail_tracker.py", "r", encoding="utf-8") as f:
        gmail_code = f.read()
    report["gmail_tracker_state_storage"] = "gmail_sync_state.json" if "gmail_sync_state.json" in gmail_code else "db_table"
    report["gmail_tracker_nudge_threshold_source"] = "settings_table" if "settings" in gmail_code.lower() else "hardcoded/env"
    
    # Check tailoring.py DB profile reading
    with open("services/tailoring.py", "r", encoding="utf-8") as f:
        tailor_code = f.read()
    report["tailoring_profile_source"] = "profile_table" if "profile" in tailor_code.lower() and "db.query" in tailor_code else "base_resume.json"
    
    # Check prep_agent.py DB reading
    with open("services/prep_agent.py", "r", encoding="utf-8") as f:
        prep_code = f.read()
    report["prep_agent_db_reading"] = {
        "skills_table": "skills" in prep_code.lower(),
        "resources_table": "resources" in prep_code.lower(),
        "resource_skills_table": "resource_skills" in prep_code.lower()
    }
    
    # Check settings table reading across codebase
    settings_hits = []
    for root, dirs, files in os.walk("."):
        if ".git" in root or "__pycache__" in root or "node_modules" in root or "audit_scripts" in root:
            continue
        for file in files:
            if file.endswith(".py"):
                filepath = os.path.join(root, file)
                with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                    if "settings" in content.lower() and ("query" in content.lower() or "select" in content.lower()):
                        settings_hits.append(filepath)
    report["files_querying_settings_table"] = settings_hits
    
    with open("audit_scripts/db_usage_report.json", "w") as f:
        json.dump(report, f, indent=2)
        
    print(json.dumps(report, indent=2))

if __name__ == "__main__":
    inspect_db_usage()
