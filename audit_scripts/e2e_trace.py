import os
import sys
import json
import time
import urllib.request
import urllib.error

sys.path.insert(0, os.path.abspath("."))

from database import SessionLocal, engine
from models import Application, GapReport, TailoredResume, ScamCheck, Notification, StatusEvent, PrepRecommendation
from sqlalchemy import text

BASE_URL = "http://127.0.0.1:8000"

def log(msg):
    print(f"[E2E-TRACE] {msg}", flush=True)

def api_post(endpoint, payload=None):
    url = f"{BASE_URL}{endpoint}"
    data = json.dumps(payload).encode('utf-8') if payload else None
    req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'}, method='POST')
    with urllib.request.urlopen(req) as resp:
        return resp.getcode(), json.loads(resp.read().decode('utf-8'))

def api_patch(endpoint, payload):
    url = f"{BASE_URL}{endpoint}"
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'}, method='PATCH')
    with urllib.request.urlopen(req) as resp:
        return resp.getcode(), json.loads(resp.read().decode('utf-8'))

def api_get(endpoint):
    url = f"{BASE_URL}{endpoint}"
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req) as resp:
        return resp.getcode(), json.loads(resp.read().decode('utf-8'))

def run_trace():
    trace_results = {}
    app_id = None
    
    try:
        # Step 1: Discover / Create Application
        log("Step 1: Discover (POST /applications)...")
        t0 = time.time()
        payload = {
            "company": "AuditTest Corp",
            "role": "Audit Test Engineer",
            "jd_text": "Requires Python, PostgreSQL, Fastapi, REST APIs, and Docker.",
            "source": "unstop",
            "is_demo": True
        }
        code, resp = api_post("/applications", payload)
        app_id = resp["id"]
        trace_results["1_discover"] = {
            "status": "PASS",
            "http_code": code,
            "response": resp,
            "time_sec": round(time.time() - t0, 3)
        }
        log(f"Step 1 PASS -> Application ID {app_id}")
    except Exception as e:
        trace_results["1_discover"] = {"status": "FAIL", "error": str(e)}
        log(f"Step 1 FAIL: {e}")
        return finalize(trace_results, app_id)

    try:
        # Step 2: Scam Check
        log("Step 2: Scam Check (POST /applications/{id}/scam-check)...")
        t0 = time.time()
        scam_payload = {
            "recruiter_name": "Audit Recruiter",
            "recruiter_domain": "audittestcorp.com",
            "message_text": "Congratulations! We would like to offer you the role."
        }
        code, resp = api_post(f"/applications/{app_id}/scam-check", scam_payload)
        trace_results["2_scam_check"] = {
            "status": "PASS",
            "http_code": code,
            "response": resp,
            "time_sec": round(time.time() - t0, 3)
        }
        log("Step 2 PASS")
    except Exception as e:
        trace_results["2_scam_check"] = {"status": "FAIL", "error": str(e)}
        log(f"Step 2 FAIL: {e}")

    try:
        # Step 3: Tailor Resume
        log("Step 3: Tailor (POST /applications/{id}/tailor)...")
        t0 = time.time()
        code, resp = api_post(f"/applications/{app_id}/tailor")
        trace_results["3_tailor"] = {
            "status": "PASS",
            "http_code": code,
            "response": resp,
            "time_sec": round(time.time() - t0, 3)
        }
        log("Step 3 PASS")
    except Exception as e:
        trace_results["3_tailor"] = {"status": "FAIL", "error": str(e)}
        log(f"Step 3 FAIL: {e}")

    try:
        # Step 4: Confirm Applied (Human Checkpoint)
        log("Step 4: Confirm Applied (POST /applications/{id}/confirm-applied)...")
        t0 = time.time()
        code, resp = api_post(f"/applications/{app_id}/confirm-applied")
        trace_results["4_confirm_applied"] = {
            "status": "PASS",
            "http_code": code,
            "response": resp,
            "time_sec": round(time.time() - t0, 3)
        }
        log("Step 4 PASS")
    except Exception as e:
        trace_results["4_confirm_applied"] = {"status": "FAIL", "error": str(e)}
        log(f"Step 4 FAIL: {e}")

    try:
        # Step 5: Simulated Gmail Signal / Status update
        log("Step 5: Status update to INTERVIEW (PATCH /applications/{id}/status)...")
        t0 = time.time()
        status_payload = {"status": "INTERVIEW", "status_source": "gmail_auto"}
        code, resp = api_patch(f"/applications/{app_id}/status", status_payload)
        trace_results["5_gmail_signal"] = {
            "status": "PASS",
            "http_code": code,
            "response": resp,
            "time_sec": round(time.time() - t0, 3)
        }
        log("Step 5 PASS")
    except Exception as e:
        trace_results["5_gmail_signal"] = {"status": "FAIL", "error": str(e)}
        log(f"Step 5 FAIL: {e}")

    try:
        # Step 6: Backdated Ghosting
        log("Step 6: Backdate + Auto-Ghost (POST /tracker/demo/backdate + POST /tracker/auto-ghost)...")
        t0 = time.time()
        code1, resp1 = api_post("/tracker/demo/backdate", {"application_id": app_id, "days_ago": 50})
        code2, resp2 = api_post("/tracker/auto-ghost")
        trace_results["6_auto_ghost"] = {
            "status": "PASS",
            "backdate_resp": resp1,
            "auto_ghost_resp": resp2,
            "time_sec": round(time.time() - t0, 3)
        }
        log("Step 6 PASS")
    except Exception as e:
        trace_results["6_auto_ghost"] = {"status": "FAIL", "error": str(e)}
        log(f"Step 6 FAIL: {e}")

    try:
        # Step 7: Gap Report
        log("Step 7: Gap Report (GET /applications/{id}/gap-report)...")
        t0 = time.time()
        code, resp = api_get(f"/applications/{app_id}/gap-report")
        trace_results["7_gap_report"] = {
            "status": "PASS",
            "http_code": code,
            "response": resp,
            "time_sec": round(time.time() - t0, 3)
        }
        log("Step 7 PASS")
    except Exception as e:
        trace_results["7_gap_report"] = {"status": "FAIL", "error": str(e)}
        log(f"Step 7 FAIL: {e}")

    try:
        # Step 8: Prep Recommendation
        log("Step 8: Prep Recommendation (GET /applications/{id}/prep)...")
        t0 = time.time()
        code, resp = api_get(f"/applications/{app_id}/prep")
        trace_results["8_prep_recommendation"] = {
            "status": "PASS",
            "http_code": code,
            "response": resp,
            "time_sec": round(time.time() - t0, 3)
        }
        log("Step 8 PASS")
    except Exception as e:
        trace_results["8_prep_recommendation"] = {"status": "FAIL", "error": str(e)}
        log(f"Step 8 FAIL: {e}")

    return finalize(trace_results, app_id)

def finalize(results, app_id):
    log("Cleaning up test row(s)...")
    db = SessionLocal()
    try:
        if app_id:
            db.execute(text("DELETE FROM prep_recommendations WHERE application_id = :id"), {"id": app_id})
            db.execute(text("DELETE FROM scam_checks WHERE application_id = :id"), {"id": app_id})
            db.execute(text("DELETE FROM status_events WHERE application_id = :id"), {"id": app_id})
            db.execute(text("UPDATE applications SET tailored_resume_id=NULL, gap_report_id=NULL WHERE id = :id"), {"id": app_id})
            db.execute(text("DELETE FROM tailored_resumes WHERE application_id = :id"), {"id": app_id})
            db.execute(text("DELETE FROM gap_reports WHERE application_id = :id"), {"id": app_id})
            db.execute(text("DELETE FROM applications WHERE id = :id"), {"id": app_id})
        
        db.execute(text("DELETE FROM applications WHERE company LIKE '%AuditTest%'"))
        db.commit()
        log("Cleanup completed successfully.")
    except Exception as ce:
        db.rollback()
        log(f"Cleanup error: {ce}")
    finally:
        db.close()

    with open("audit_scripts/e2e_report.json", "w") as f:
        json.dump(results, f, indent=2)
        
    print(json.dumps(results, indent=2))
    return results

if __name__ == "__main__":
    run_trace()
