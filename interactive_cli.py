#!/usr/bin/env python3
"""
Placement Copilot - Complete Interactive CLI Command Center
Control and execute all 6 autonomous agents from a single interactive terminal:
1. Scout Agent     - Job Discovery & Sentence-Transformer Embedding Matching
2. Tailoring Agent - Deterministic LaTeX Resume Reordering & PDF Compilation
3. Tracker Agent   - Gmail Sync (OAuth/Mock), Manual Status, 45-day Auto-Ghost
4. Scam-Check Agent- Recruiter Fraud Screening (Rule Layer + Ollama LLM Explanation)
5. Prep Agent       - Interview Answer Evaluation (Keyword Coverage + Ollama Feedback)
6. Gap Agent        - Per-Row & Aggregate Skill Gap Analytics across Rejections/Ghosting
"""

import os
import sys
import json
import urllib.request
import urllib.error

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
MODEL_SERVICE_URL = os.getenv("MODEL_SERVICE_URL", "http://localhost:8001")


def print_banner():
    print("\n" + "=" * 80)
    print(" 🚀 PLACEMENT COPILOT — AGENTIC AI COMMAND CENTER")
    print(" Off-Campus Job Search, Resume Tailoring, Tracking & Prep System")
    print("=" * 80)


def http_request(url: str, method: str = "GET", payload: dict = None) -> dict:
    headers = {"Content-Type": "application/json"} if payload is not None else {}
    data_bytes = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url, data=data_bytes, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req, timeout=40) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8") if e.fp else "{}"
        try:
            err_json = json.loads(body)
        except Exception:
            err_json = {"error": "http_error", "detail": body}
        return {"_error_status": e.code, "_error_body": err_json}
    except Exception as e:
        return {"_error_status": 500, "_error_body": {"error": "network_error", "detail": str(e)}}


def check_services():
    print(f"\n[INFO] Connecting to Backend at {BACKEND_URL} ...")
    b_health = http_request(f"{BACKEND_URL}/health")
    if b_health.get("status") == "ok":
        print(f"  └─ Backend Server: READY (status: ok)")
    else:
        print(f"  └─ Backend Server: UNREACHABLE ({b_health.get('_error_body')})")
        print("  ⚠️  Please run 'python main.py' in a separate terminal!")

    print(f"[INFO] Connecting to Model Service at {MODEL_SERVICE_URL} ...")
    m_health = http_request(f"{MODEL_SERVICE_URL}/health")
    if m_health.get("model_loaded") is True:
        print(f"  └─ Model Service: READY (sentence-transformers loaded)")
    else:
        print(f"  └─ Model Service: UNREACHABLE or LOADING")
        print("  ⚠️  Please run 'python model-service/main.py' in a separate terminal!")


def run_scout_agent():
    print("\n" + "=" * 80)
    print(" 🔍 SCOUT AGENT — JOB DISCOVERY & EMBEDDING MATCH")
    print("=" * 80)
    print("1. Trigger Job Sourcing Poller (SerpAPI / Unstop / Mock)")
    print("2. Preview Sourcing in Dry-Run Mode (No DB write)")
    print("3. Manually Submit Job Description for Embedding Match")
    choice = input("\nSelect option (1-3) [Default 1]: ").strip() or "1"

    if choice == "2":
        res = http_request(f"{BACKEND_URL}/scout/sync?dry_run=true", method="POST")
        print("\n--- Dry-Run Preview Results ---")
        print(json.dumps(res, indent=2))
    elif choice == "3":
        company = input("Company Name: ").strip() or "Skydio"
        role = input("Role Title: ").strip() or "CV Engineer"
        jd = input("Job Description: ").strip() or "Looking for CV engineer with YOLOv8, PyTorch, GeoTIFF imagery."
        source = input("Source (serpapi/unstop) [Default serpapi]: ").strip() or "serpapi"

        payload = {"company": company, "role": role, "jd_text": jd, "source": source}
        res = http_request(f"{BACKEND_URL}/applications", method="POST", payload=payload)
        print("\n--- Created Application Entry ---")
        print(json.dumps(res, indent=2))
    else:
        res = http_request(f"{BACKEND_URL}/scout/sync?dry_run=false", method="POST")
        print("\n--- Job Sourcing Sync Results ---")
        print(json.dumps(res, indent=2))


def run_tailoring_agent():
    print("\n" + "=" * 80)
    print(" 📄 TAILORING AGENT — LATEX RESUME REORDERING & PDF GENERATION")
    print("=" * 80)
    apps_res = http_request(f"{BACKEND_URL}/applications")
    apps = apps_res.get("applications", [])

    if not apps:
        print("No applications found in DB. Please run Scout Agent first!")
        return

    print("Available Applications:")
    for app in apps:
        print(f"  [{app['id']}] {app['company']} - {app['role']} (Status: {app['status']})")

    app_id_str = input(f"\nEnter Application ID to tailor resume for [Default {apps[0]['id']}]: ").strip()
    app_id = int(app_id_str) if app_id_str.isdigit() else apps[0]['id']

    print(f"\n[INFO] Running Tailoring Agent on Application ID {app_id}...")
    res = http_request(f"{BACKEND_URL}/applications/{app_id}/tailor", method="POST")

    if "_error_status" in res:
        print(f"[FAIL] Tailoring failed: {res['_error_body']}")
        return

    resume_data = res.get("resume_data", {})
    bullets = resume_data.get("ordered_bullets", [])
    print("\n--- Reordered Resume Bullets (TF-IDF Keyword Score) ---")
    for b in bullets:
        print(f"  - [{b.get('score'):.4f}] {b.get('project')}: {b.get('bullet')[:80]}...")

    print(f"\n✅ Created Tailored Resume ID : {res.get('tailored_resume_id')}")
    print(f"✅ Generated LaTeX Resume File  : tailored_resume.tex")
    print(f"✅ Status updated to READY_TO_APPLY")


def run_tracker_agent():
    print("\n" + "=" * 80)
    print(" 📬 TRACKER AGENT — GMAIL OAUTH, STATUS & STALENESS MONITOR")
    print("=" * 80)
    print("1. Trigger Gmail Inbox Sync (OAuth / Mock Fixtures)")
    print("2. Check Tracker Connection & Sync Status")
    print("3. Update Application Status Manually")
    choice = input("\nSelect option (1-3) [Default 1]: ").strip() or "1"

    if choice == "2":
        res = http_request(f"{BACKEND_URL}/tracker/gmail/status")
        print("\n--- Tracker Status ---")
        print(json.dumps(res, indent=2))
    elif choice == "3":
        app_id = input("Application ID: ").strip() or "1"
        new_status = input("New Status (APPLIED/OA_INVITE/INTERVIEW/REJECTED/GHOSTED/OFFER): ").strip().upper() or "INTERVIEW"
        status_src = input("Status Source (manual/gmail_auto/auto_ghost) [Default manual]: ").strip() or "manual"

        payload = {"status": new_status, "status_source": status_src}
        res = http_request(f"{BACKEND_URL}/applications/{app_id}/status", method="PATCH", payload=payload)
        print("\n--- Updated Application ---")
        print(json.dumps(res, indent=2))
    else:
        # Default mock fixture sync
        mock_payload = {
            "mock_messages": [
                {
                    "id": "msg_cli_01",
                    "sender": "recruiter@razorpay.com",
                    "subject": "Update on your Razorpay Application",
                    "body": "Thank you for applying. Unfortunately, we have decided to move forward with other candidates."
                }
            ]
        }
        res = http_request(f"{BACKEND_URL}/tracker/gmail/sync", method="POST", payload=mock_payload)
        print("\n--- Gmail Sync Results ---")
        print(json.dumps(res, indent=2))


def run_scam_check_agent():
    print("\n" + "=" * 80)
    print(" 🛡️ SCAM-CHECK AGENT — RECRUITER FRAUD SCREENING")
    print("=" * 80)
    apps_res = http_request(f"{BACKEND_URL}/applications")
    apps = apps_res.get("applications", [])
    app_id = apps[0]["id"] if apps else 1

    recruiter_name = input("Recruiter Name [Default Rohan Sharma]: ").strip() or "Rohan Sharma"
    recruiter_domain = input("Recruiter Email/Domain [Default technova-careers.in]: ").strip() or "technova-careers.in"
    company = input("Claimed Company [Default TechNova Solutions]: ").strip() or "TechNova Solutions"

    payload = {
        "recruiter_name": recruiter_name,
        "recruiter_domain": recruiter_domain,
        "claimed_company": company,
    }

    print(f"\n[INFO] Running Scam-Check Rule Layer + Ollama LLM Explanation...")
    res = http_request(f"{BACKEND_URL}/applications/{app_id}/scam-check", method="POST", payload=payload)

    if "_error_status" in res:
        print(f"[FAIL] Scam check failed: {res['_error_body']}")
        return

    print("\n--- Scam Check Assessment ---")
    print(f"Risk Score      : {res.get('risk_score', 0):.2f} (Scale 0.0 - 1.0)")
    print("Flagged Reasons :")
    for r in res.get("flagged_reasons", []):
        print(f"  - 🚩 {r}")
    print(f"LLM Explanation : \"{res.get('explanation_text')}\"")


def run_prep_agent():
    print("\n" + "=" * 80)
    print(" 🎯 PREP AGENT — INTERVIEW ANSWER EVALUATION")
    print("=" * 80)
    apps_res = http_request(f"{BACKEND_URL}/applications")
    apps = apps_res.get("applications", [])
    app_id = apps[0]["id"] if apps else 1

    question = input("\nInterview Question [Default: Walk me through hard-negative mining in drone imagery]: ").strip() or "Walk me through hard-negative mining in drone imagery."
    answer = input("Your Answer: ").strip() or "I used sliding window tiling across GeoTIFF images and filtered false positives based on confidence thresholds."
    tags_str = input("Question Tags (comma separated) [Default: hard negative mining, sliding window tiling, confidence thresholding]: ").strip()
    
    tags = [t.strip() for t in tags_str.split(",")] if tags_str else ["hard negative mining", "sliding window tiling", "confidence thresholding"]

    payload = {
        "question": question,
        "student_answer": answer,
        "question_tags": tags,
    }

    print(f"\n[INFO] Evaluating Answer (Deterministic Coverage + Ollama Qualitative Feedback)...")
    res = http_request(f"{BACKEND_URL}/applications/{app_id}/prep/evaluate-answer", method="POST", payload=payload)

    if "_error_status" in res:
        print(f"[FAIL] Prep evaluation failed: {res['_error_body']}")
        return

    print("\n--- Answer Evaluation ---")
    print(f"Keyword Coverage : {res.get('keyword_coverage', 0):.2f} (Deterministic signal)")
    print(f"Flagged as Weak  : {res.get('flagged_as_weak')}")
    print(f"LLM Feedback     : \"{res.get('feedback_text')}\"")

    recs = res.get("recommended_resources", [])
    if recs:
        print("\n📚 Recommended Learning Resources & Documentation:")
        for item in recs:
            print(f"  - [{item.get('skill')}] {item.get('title')}: {item.get('url')}")

    suggs = res.get("actionable_suggestions", [])
    if suggs:
        print("\n💡 Actionable Improvement Suggestions:")
        for s in suggs:
            print(f"  - {s}")


def run_gap_agent():
    print("\n" + "=" * 80)
    print(" 📊 GAP AGENT — REJECTION & GHOSTING SKILL GAP ANALYTICS")
    print("=" * 80)
    print("1. View Aggregate Skill Gap Report across all rejections")
    print("2. View Per-Row Skill Gap Report for specific application")
    choice = input("\nSelect option (1-2) [Default 1]: ").strip() or "1"

    if choice == "2":
        app_id = input("Application ID: ").strip() or "3"
        res = http_request(f"{BACKEND_URL}/applications/{app_id}/gap-report")
        print("\n--- Per-Row Gap Report ---")
        print(json.dumps(res, indent=2))
    else:
        res = http_request(f"{BACKEND_URL}/gap-report")
        print("\n--- Aggregate Gap Analysis Report ---")
        print(json.dumps(res, indent=2))


def run_full_pipeline():
    print("\n" + "=" * 80)
    print(" 🚀 RUNNING FULL 6-AGENT AUTOMATED E2E PIPELINE WALKTHROUGH")
    print("=" * 80)
    import run_all_agents_cli
    run_all_agents_cli.main()


def main_menu():
    check_services()
    while True:
        print_banner()
        print(" 1. 🔍  Scout Agent     - Job Discovery & Embedding Match")
        print(" 2. 📄  Tailoring Agent - Tailor LaTeX Resume (.tex & PDF)")
        print(" 3. 📬  Tracker Agent   - Gmail Sync (OAuth/Mock) & Status Control")
        print(" 4. 🛡️  Scam-Check Agent- Recruiter Fraud Screening (Rule + Ollama)")
        print(" 5. 🎯  Prep Agent       - Practice Interview Q&A Feedback")
        print(" 6. 📊  Gap Agent        - Skill Gap Analytics (Per-row & Aggregate)")
        print(" 7. 🚀  Run All 6 Agents - Automated E2E Pipeline Walkthrough")
        print(" 8. ❌  Exit")
        print("=" * 80)

        choice = input("Enter choice (1-8): ").strip()
        if choice == "1":
            run_scout_agent()
        elif choice == "2":
            run_tailoring_agent()
        elif choice == "3":
            run_tracker_agent()
        elif choice == "4":
            run_scam_check_agent()
        elif choice == "5":
            run_prep_agent()
        elif choice == "6":
            run_gap_agent()
        elif choice == "7":
            run_full_pipeline()
        elif choice == "8" or choice.lower() == "exit":
            print("\nExiting Placement Copilot CLI. Goodbye!")
            sys.exit(0)
        else:
            print("\nInvalid selection! Please enter a number between 1 and 8.")

        input("\nPress Enter to return to main menu...")


if __name__ == "__main__":
    main_menu()
