import os
import re
import sys
import json
import glob
import urllib.request
import urllib.error
from database import SessionLocal
from models import Application, TailoredResume, GapReport, ScamCheck

def print_header(title):
    print("\n" + "=" * 80)
    print(f" {title}")
    print("=" * 80)

def http_post(url, payload):
    data_bytes = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data_bytes, headers={'Content-Type': 'application/json'}, method='POST')
    with urllib.request.urlopen(req, timeout=40) as resp:
        return json.loads(resp.read().decode('utf-8'))

def http_get(url):
    req = urllib.request.Request(url, method='GET')
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode('utf-8'))

def http_patch(url, payload):
    data_bytes = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data_bytes, headers={'Content-Type': 'application/json'}, method='PATCH')
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode('utf-8'))


# ==============================================================================
# CHECK 1: OLLAMA REAL GENERATION CHECK
# ==============================================================================
def check_1_ollama():
    print_header("CHECK 1: OLLAMA REAL GENERATION CHECK")
    ms_url = "http://localhost:8001/llm-generate"
    
    # 1.1 scam_explanation
    scam_payload = {
        "task_type": "scam_explanation",
        "context": {
            "flagged_reasons": [
                "sender domain technova-careers.in does not match TechNova official domain",
                "requests processing fee before interview"
            ],
            "recruiter_info": {
                "name": "Rohan Sharma",
                "claimed_company": "TechNova Solutions",
                "email_domain": "technova-careers.in"
            }
        }
    }
    
    # 1.2 prep_recommendations
    prep_payload = {
        "task_type": "prep_recommendations",
        "context": {
            "jd_summary": "Looking for Python engineer experienced in PyTorch and Docker.",
            "candidates": [
                {"id": 1, "title": "PyTorch Tutorial", "skills": ["pytorch"]},
                {"id": 2, "title": "Docker Crash Course", "skills": ["docker"]}
            ]
        }
    }
    
    # 1.3 gap_summary
    gap_payload = {
        "task_type": "gap_summary",
        "context": {
            "rejected_applications": [
                {"company": "Innovaccer", "role_tag": "SDE-1", "rejection_stage": "OA_INVITE"},
                {"company": "Razorpay", "role_tag": "SDE Intern", "rejection_stage": "OA_INVITE"},
                {"company": "Zeta Suite", "role_tag": "SDE", "rejection_stage": "OA_INVITE"},
                {"company": "Skylark Labs", "role_tag": "ML Engineer", "rejection_stage": "INTERVIEW"}
            ]
        }
    }
    
    res1 = http_post(ms_url, scam_payload)
    res2 = http_post(ms_url, prep_payload)
    res3 = http_post(ms_url, gap_payload)
    
    print("\n--- 1.1 task_type: scam_explanation ---")
    print(f"Error field present? {'YES' if 'error' in res1 else 'NO (ABSENT)'}")
    print("Full generated_text:")
    print(f"\"{res1.get('generated_text')}\"")
    
    print("\n--- 1.2 task_type: prep_recommendations ---")
    print(f"Error field present? {'YES' if 'error' in res2 else 'NO (ABSENT)'}")
    print("Full generated_text:")
    print(f"\"{res2.get('generated_text')}\"")
    
    print("\n--- 1.3 task_type: gap_summary ---")
    print(f"Error field present? {'YES' if 'error' in res3 else 'NO (ABSENT)'}")
    print("Full generated_text:")
    print(f"\"{res3.get('generated_text')}\"")
    
    # Assertions
    assert "error" not in res1 and res1.get("generated_text")
    assert "error" not in res2 and res2.get("generated_text")
    assert "error" not in res3 and res3.get("generated_text")
    assert res1["generated_text"] != res2["generated_text"] != res3["generated_text"]
    
    print("\nSTATUS: CHECK 1 PASSED!")
    return True


# ==============================================================================
# CHECK 2: FULL END-TO-END FLOW TEST
# ==============================================================================
def check_2_e2e_flow():
    print_header("CHECK 2: FULL END-TO-END FLOW TEST")
    base_url = "http://localhost:8000"
    
    # Step a: POST /applications
    print("\n--- Step a: POST /applications ---")
    create_payload = {
        "company": "Scale AI E2E Test",
        "role": "AI Solutions Engineer",
        "jd_text": "Strong Python, PyTorch, LLM fine-tuning, system design, and computer vision skills required.",
        "source": "adzuna"
    }
    app_res = http_post(f"{base_url}/applications", create_payload)
    app_id = app_res["id"]
    print(f"Created Application ID: {app_id}")
    print("Response payload:")
    print(json.dumps(app_res, indent=2))
    assert app_res["status"] in ("DISCOVERED", "READY_TO_APPLY")
    
    # Step b: POST /applications/{id}/confirm-applied
    print(f"\n--- Step b: POST /applications/{app_id}/confirm-applied ---")
    confirm_res = http_post(f"{base_url}/applications/{app_id}/confirm-applied", {})
    print("Response payload:")
    print(json.dumps(confirm_res, indent=2))
    assert confirm_res["status"] == "APPLIED"
    
    # Step c: PATCH /applications/{id}/status -> GHOSTED
    print(f"\n--- Step c: PATCH /applications/{app_id}/status -> GHOSTED ---")
    patch_payload = {
        "status": "GHOSTED",
        "status_source": "auto_ghost"
    }
    patch_res = http_patch(f"{base_url}/applications/{app_id}/status", patch_payload)
    print("Response payload:")
    print(json.dumps(patch_res, indent=2))
    assert patch_res["status"] == "GHOSTED"
    assert patch_res["gap_report_id"] is not None
    
    # Step d: GET /applications/{id}/gap-report
    print(f"\n--- Step d: GET /applications/{app_id}/gap-report ---")
    gap_res = http_get(f"{base_url}/applications/{app_id}/gap-report")
    print("Response payload:")
    print(json.dumps(gap_res, indent=2))
    assert gap_res["application_id"] == app_id
    assert gap_res["summary_text"] and "fallback" not in gap_res["summary_text"].lower()
    
    # Step e: POST /applications/{id}/scam-check
    print(f"\n--- Step e: POST /applications/{app_id}/scam-check ---")
    scam_payload = {
        "recruiter_name": "Vikram Singh",
        "recruiter_domain": "scaleai-recruiting-jobs.com",
        "claimed_company": "Scale AI"
    }
    scam_res = http_post(f"{base_url}/applications/{app_id}/scam-check", scam_payload)
    print("Response payload:")
    print(json.dumps(scam_res, indent=2))
    assert scam_res["risk_score"] > 0
    assert len(scam_res["flagged_reasons"]) > 0
    assert scam_res["explanation_text"] is not None

    # Step f: PATCH /applications/{id}/status -> INTERVIEW & GET /applications/{id}/prep
    print(f"\n--- Step f: Transition status to INTERVIEW & test Prep Agent ---")
    status_res = http_patch(f"{base_url}/applications/{app_id}/status", {"status": "INTERVIEW"})
    assert status_res["status"] == "INTERVIEW"
    
    prep_res = http_get(f"{base_url}/applications/{app_id}/prep")
    print("Prep recommendations payload:")
    print(json.dumps(prep_res, indent=2))
    assert prep_res["application_id"] == app_id
    assert "recommendations" in prep_res
    assert isinstance(prep_res["recommendations"], list)

    print("\nSTATUS: CHECK 2 PASSED!")
    return True


# ==============================================================================
# CHECK 3: DATA INTEGRITY CHECK
# ==============================================================================
def check_3_data_integrity():
    print_header("CHECK 3: DATA INTEGRITY CHECK")
    db = SessionLocal()
    
    apps = db.query(Application).all()
    print(f"Total Applications in DB: {len(apps)}")
    for a in apps:
        print(f"  ID={a.id}: {a.company} | {a.role} | status={a.status}")
        
    # Verify original 5 seed rows exist (IDs 1, 2, 3, 4, 5)
    app_ids = set(a.id for a in apps)
    seed_ids = {1, 2, 3, 4, 5}
    assert seed_ids.issubset(app_ids), f"Missing seed IDs! Present IDs: {app_ids}"
    print("\nVerified original 5 seed rows (IDs 1-5) are all intact.")
    
    # Check foreign keys in related tables
    tailored = db.query(TailoredResume).all()
    gap_reports = db.query(GapReport).all()
    scam_checks = db.query(ScamCheck).all()
    
    print(f"TailoredResumes count: {len(tailored)}")
    print(f"GapReports count: {len(gap_reports)}")
    print(f"ScamChecks count: {len(scam_checks)}")
    
    for t in tailored:
        assert t.application_id in app_ids, f"Orphaned TailoredResume ID {t.id} -> application_id {t.application_id}"
    for g in gap_reports:
        if g.application_id is not None:
            assert g.application_id in app_ids, f"Orphaned GapReport ID {g.id} -> application_id {g.application_id}"
    for s in scam_checks:
        if s.application_id is not None:
            assert s.application_id in app_ids, f"Orphaned ScamCheck ID {s.id} -> application_id {s.application_id}"
            
    print("Verified zero orphaned foreign keys in tailored_resumes, gap_reports, or scam_checks.")
    db.close()
    
    print("\nSTATUS: CHECK 3 PASSED!")
    return True


# ==============================================================================
# CHECK 4: ENUM VALUE FINAL CHECK
# ==============================================================================
def check_4_enum_values():
    print_header("CHECK 4: ENUM VALUE FINAL CHECK")
    py_files = glob.glob("**/*.py", recursive=True)
    
    invalid_oa_matches = []
    invalid_result_matches = []
    
    # Regex to catch "OA" used as standalone status string, not "OA_INVITE"
    oa_regex = re.compile(r'["\']OA["\']')
    result_regex = re.compile(r'["\']RESULT["\']')
    
    for py_file in py_files:
        if ".venv" in py_file or "git" in py_file:
            continue
        with open(py_file, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
            for idx, line in enumerate(lines, 1):
                if oa_regex.search(line):
                    invalid_oa_matches.append(f"{py_file}:{idx}: {line.strip()}")
                if result_regex.search(line):
                    invalid_result_matches.append(f"{py_file}:{idx}: {line.strip()}")
                    
    print(f"Scanned {len(py_files)} Python files.")
    print(f"Literal 'OA' status occurrences: {len(invalid_oa_matches)}")
    if invalid_oa_matches:
        for m in invalid_oa_matches:
            print("  " + m)
            
    print(f"Literal 'RESULT' status occurrences: {len(invalid_result_matches)}")
    if invalid_result_matches:
        for m in invalid_result_matches:
            print("  " + m)
            
    assert len(invalid_oa_matches) == 0, f"Found invalid 'OA' status occurrences: {invalid_oa_matches}"
    assert len(invalid_result_matches) == 0, f"Found invalid 'RESULT' status occurrences: {invalid_result_matches}"
    
    print("\nSTATUS: CHECK 4 PASSED!")
    return True


# ==============================================================================
# CHECK 5: CLEAN RESTART TEST
# ==============================================================================
def check_5_clean_restart():
    print_header("CHECK 5: CLEAN RESTART TEST")
    
    url_8001 = "http://localhost:8001/health"
    url_8000 = "http://localhost:8000/health"
    
    res1 = http_get(url_8001)
    res2 = http_get(url_8000)
    
    print(f"GET {url_8001} response:")
    print(json.dumps(res1, indent=2))
    
    print(f"\nGET {url_8000} response:")
    print(json.dumps(res2, indent=2))
    
    assert res1.get("status") == "ok" and res1.get("model_loaded") is True
    assert res2.get("status") == "ok" and res2.get("service") == "placement-copilot-backend"
    
    print("\nSTATUS: CHECK 5 PASSED!")
    return True

if __name__ == "__main__":
    try:
        check_1_ollama()
        check_2_e2e_flow()
        check_3_data_integrity()
        check_4_enum_values()
        check_5_clean_restart()
        print("\n" + "=" * 80)
        print(" ALL 5 PRE-PUSH VERIFICATION CHECKS PASSED SUCCESSFULLY!")
        print("=" * 80)
    except Exception as e:
        print(f"\n[FAILURE] Pre-push verification failed: {e}")
        sys.exit(1)
