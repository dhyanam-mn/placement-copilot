#!/usr/bin/env python3
"""
Placement Copilot - End-to-End Multi-Agent CLI Walkthrough
Exercises all six agents (Scout, Tailoring, Tracker, Scam-Check, Prep, Gap)
against live backend (http://localhost:8000) and model-service (http://localhost:8001).
"""

import os
import sys
import json
import urllib.request
import urllib.error

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
MODEL_SERVICE_URL = os.getenv("MODEL_SERVICE_URL", "http://localhost:8001")

def print_header(agent_name: str):
    print("\n" + "=" * 80)
    print(f"=== AGENT: {agent_name} ===")
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

def main():
    print("================================================================================")
    print(" PLACEMENT COPILOT - MULTI-AGENT LIVE END-TO-END CLI WALKTHROUGH")
    print("================================================================================")
    print(f"Connecting to Backend: {BACKEND_URL}")
    print(f"Connecting to Model Service: {MODEL_SERVICE_URL}")

    # Check initial health
    b_health = http_request(f"{BACKEND_URL}/health")
    if b_health.get("status") != "ok":
        print(f"[FAIL] Backend server not reachable at {BACKEND_URL}/health")
        sys.exit(1)
        
    m_health = http_request(f"{MODEL_SERVICE_URL}/health")
    if m_health.get("model_loaded") is not True:
        print(f"[FAIL] Model service not ready at {MODEL_SERVICE_URL}/health")
        sys.exit(1)

    results_summary = []
    app_id = None

    # --------------------------------------------------------------------------
    # 1. SCOUT AGENT
    # --------------------------------------------------------------------------
    print_header("Scout")
    scout_payload = {
        "company": "Skydio",
        "role": "Computer Vision Pipeline Engineer",
        "jd_text": "Seeking a Computer Vision Engineer experienced in object detection pipelines, YOLOv8 model optimization, PyTorch, GeoTIFF satellite imagery, rasterio, and drone spatial analytics.",
        "source": "unstop"
    }
    scout_resp = http_request(f"{BACKEND_URL}/applications", method="POST", payload=scout_payload)
    
    if "_error_status" in scout_resp:
        print(f"[ERROR] Scout Agent failed with status {scout_resp['_error_status']}:")
        print(json.dumps(scout_resp["_error_body"], indent=2))
        results_summary.append(("Scout", "FAIL", "Failed to create application entry"))
        sys.exit(1)
        
    app_id = scout_resp.get("id")
    status = scout_resp.get("status")
    match_score = scout_resp.get("match_score")
    
    print(f"Created Application ID : {app_id}")
    print(f"Company & Role         : {scout_resp.get('company')} - {scout_resp.get('role')}")
    print(f"Initial Status         : {status} (Expected: DISCOVERED)")
    print(f"Scout Match Score      : {match_score} (Cosine Similarity via /embed)")
    
    if status == "DISCOVERED" and isinstance(match_score, (int, float)):
        print("\nSTATUS: PASS [Scout Agent successfully created entry with status DISCOVERED]")
        results_summary.append(("Scout", "PASS", f"App ID {app_id} created | status: DISCOVERED | match_score: {match_score}"))
    else:
        print("\nSTATUS: FAIL [Unexpected status or match score format]")
        results_summary.append(("Scout", "FAIL", f"Unexpected status '{status}'"))
        sys.exit(1)

    # --------------------------------------------------------------------------
    # 2. TAILORING AGENT
    # --------------------------------------------------------------------------
    print_header("Tailoring")
    tailor_resp = http_request(f"{BACKEND_URL}/applications/{app_id}/tailor", method="POST", payload={})
    
    if "_error_status" in tailor_resp:
        print(f"[ERROR] Tailoring Agent failed with status {tailor_resp['_error_status']}:")
        print(json.dumps(tailor_resp["_error_body"], indent=2))
        results_summary.append(("Tailoring", "FAIL", "Failed to tailor resume"))
        sys.exit(1)

    resume_data = tailor_resp.get("resume_data", {})
    ordered_bullets = resume_data.get("ordered_bullets", [])
    pdf_path = resume_data.get("pdf_path") or os.path.abspath("tailored_resume.pdf")
    
    print(f"Tailored Resume ID : {tailor_resp.get('tailored_resume_id')}")
    print("Ordered Resume Bullets (by Jaccard similarity score):")
    for b in ordered_bullets:
        print(f"  - [{b.get('score'):.4f}] {b.get('id')}")
        
    pdf_exists = os.path.exists(pdf_path)
    pdf_size = os.path.getsize(pdf_path) if pdf_exists else 0
    print(f"Generated PDF File : {pdf_path}")
    print(f"PDF Size           : {pdf_size} bytes (Exists: {pdf_exists})")

    if len(ordered_bullets) > 0 and pdf_exists and pdf_size > 0:
        print("\nSTATUS: PASS [Tailoring Agent reordered bullets and compiled PDF output]")
        results_summary.append(("Tailoring", "PASS", f"Reordered {len(ordered_bullets)} bullets | PDF generated ({pdf_size} B)"))
    else:
        print("\nSTATUS: FAIL [PDF missing or zero bullets returned]")
        results_summary.append(("Tailoring", "FAIL", "PDF compilation failed or missing bullets"))
        sys.exit(1)

    # --------------------------------------------------------------------------
    # 3. TRACKER AGENT
    # --------------------------------------------------------------------------
    print_header("Tracker")
    
    # Transition 1: APPLIED (manual)
    patch1_resp = http_request(
        f"{BACKEND_URL}/applications/{app_id}/status",
        method="PATCH",
        payload={"status": "APPLIED", "status_source": "manual"}
    )
    if "_error_status" in patch1_resp:
        print(f"[ERROR] Tracker Agent Transition 1 failed:")
        print(json.dumps(patch1_resp["_error_body"], indent=2))
        results_summary.append(("Tracker", "FAIL", "Transition to APPLIED failed"))
        sys.exit(1)
        
    print(f"Transition 1 -> Status: {patch1_resp.get('status')} | Source: {patch1_resp.get('status_source')}")

    # Transition 2: INTERVIEW (gmail_auto)
    patch2_resp = http_request(
        f"{BACKEND_URL}/applications/{app_id}/status",
        method="PATCH",
        payload={"status": "INTERVIEW", "status_source": "gmail_auto"}
    )
    if "_error_status" in patch2_resp:
        print(f"[ERROR] Tracker Agent Transition 2 failed:")
        print(json.dumps(patch2_resp["_error_body"], indent=2))
        results_summary.append(("Tracker", "FAIL", "Transition to INTERVIEW failed"))
        sys.exit(1)

    print(f"Transition 2 -> Status: {patch2_resp.get('status')} | Source: {patch2_resp.get('status_source')}")

    if patch1_resp.get("status") == "APPLIED" and patch2_resp.get("status") == "INTERVIEW":
        print("\nSTATUS: PASS [Tracker Agent recorded lifecycle status transitions]")
        results_summary.append(("Tracker", "PASS", "APPLIED (manual) -> INTERVIEW (gmail_auto)"))
    else:
        print("\nSTATUS: FAIL [Lifecycle transitions mismatch]")
        results_summary.append(("Tracker", "FAIL", "Status transition mismatch"))
        sys.exit(1)

    # --------------------------------------------------------------------------
    # 4. SCAM-CHECK AGENT
    # --------------------------------------------------------------------------
    print_header("Scam-Check")
    scam_payload = {
        "recruiter_name": "Rohan Sharma",
        "recruiter_domain": "skydio-careers.in",
        "claimed_company": "Skydio"
    }
    scam_resp = http_request(f"{BACKEND_URL}/applications/{app_id}/scam-check", method="POST", payload=scam_payload)
    
    if "_error_status" in scam_resp:
        print(f"[ERROR] Scam-Check Agent failed:")
        print(json.dumps(scam_resp["_error_body"], indent=2))
        results_summary.append(("Scam-Check", "FAIL", "Scam check execution error"))
        sys.exit(1)

    risk_score = scam_resp.get("risk_score")
    flagged_reasons = scam_resp.get("flagged_reasons", [])
    explanation_text = scam_resp.get("explanation_text")
    
    print(f"Risk Score      : {risk_score:.2f} (Scale 0.0 - 1.0)")
    print("Flagged Reasons :")
    for r in flagged_reasons:
        print(f"  - {r}")
    print(f"LLM Explanation : \"{explanation_text}\"")

    llm_ok = explanation_text and "llm_unavailable" not in explanation_text
    if isinstance(risk_score, (int, float)) and len(flagged_reasons) > 0 and llm_ok:
        print("\nSTATUS: PASS [Scam-Check Agent flagged risk & generated LLM explanation]")
        results_summary.append(("Scam-Check", "PASS", f"Risk score: {risk_score:.2f} | {len(flagged_reasons)} flags | LLM explanation OK"))
    else:
        print("\nSTATUS: FAIL [Missing risk score, reasons, or LLM explanation]")
        results_summary.append(("Scam-Check", "FAIL", "Missing risk score or LLM explanation"))
        sys.exit(1)

    # --------------------------------------------------------------------------
    # 5. PREP AGENT
    # --------------------------------------------------------------------------
    print_header("Prep")
    prep_payload = {
        "question": "Walk me through your approach to hard-negative mining in the DronaMaps pipeline.",
        "student_answer": "I used sliding window tiling across GeoTIFF images and filtered false positives based on confidence thresholds.",
        "question_tags": ["hard negative mining", "sliding window tiling", "confidence thresholding"]
    }
    prep_resp = http_request(f"{BACKEND_URL}/applications/{app_id}/prep/evaluate-answer", method="POST", payload=prep_payload)

    if "_error_status" in prep_resp:
        print(f"[ERROR] Prep Agent failed:")
        print(json.dumps(prep_resp["_error_body"], indent=2))
        results_summary.append(("Prep", "FAIL", "Prep evaluate answer execution error"))
        sys.exit(1)

    keyword_coverage = prep_resp.get("keyword_coverage")
    flagged_as_weak = prep_resp.get("flagged_as_weak")
    feedback_text = prep_resp.get("feedback_text")

    print(f"Keyword Coverage : {keyword_coverage:.2f} (Deterministic signal)")
    print(f"Flagged as Weak  : {flagged_as_weak}")
    print(f"LLM Feedback     : \"{feedback_text}\"")

    if isinstance(keyword_coverage, (int, float)) and isinstance(flagged_as_weak, bool) and feedback_text:
        print("\nSTATUS: PASS [Prep Agent evaluated answer with deterministic check + qualitative feedback]")
        results_summary.append(("Prep", "PASS", f"Coverage: {keyword_coverage:.2f} | Weak: {flagged_as_weak} | LLM Feedback OK"))
    else:
        print("\nSTATUS: FAIL [Missing keyword coverage or feedback text]")
        results_summary.append(("Prep", "FAIL", "Missing feedback output"))
        sys.exit(1)

    # --------------------------------------------------------------------------
    # 6. GAP AGENT
    # --------------------------------------------------------------------------
    print_header("Gap")
    
    # 6a. Move to REJECTED to trigger gap report
    rej_resp = http_request(
        f"{BACKEND_URL}/applications/{app_id}/status",
        method="PATCH",
        payload={"status": "REJECTED", "status_source": "gmail_auto"}
    )
    if "_error_status" in rej_resp:
        print(f"[ERROR] Moving application to REJECTED failed:")
        print(json.dumps(rej_resp["_error_body"], indent=2))
        results_summary.append(("Gap", "FAIL", "Failed to set REJECTED status"))
        sys.exit(1)
        
    print(f"Status Updated  : REJECTED | gap_report_id: {rej_resp.get('gap_report_id')}")

    # 6b. GET per-row gap report
    per_row_gap = http_request(f"{BACKEND_URL}/applications/{app_id}/gap-report", method="GET")
    if "_error_status" in per_row_gap:
        print(f"[ERROR] Fetching per-row gap report failed:")
        print(json.dumps(per_row_gap["_error_body"], indent=2))
        results_summary.append(("Gap", "FAIL", "Per-row gap report error"))
        sys.exit(1)
        
    print(f"Per-Row Gap Summary : \"{per_row_gap.get('summary_text')}\"")
    print(f"Computed Details    : {json.dumps(per_row_gap.get('details'), indent=2)}")

    # 6c. GET aggregate gap report
    agg_gap = http_request(f"{BACKEND_URL}/gap-report", method="GET")
    if "_error_status" in agg_gap:
        print(f"[ERROR] Fetching aggregate gap report failed:")
        print(json.dumps(agg_gap["_error_body"], indent=2))
        results_summary.append(("Gap", "FAIL", "Aggregate gap report error"))
        sys.exit(1)
        
    print(f"Aggregate Summary   : \"{agg_gap.get('summary_text')}\"")

    if per_row_gap.get("summary_text") and agg_gap.get("summary_text"):
        print("\nSTATUS: PASS [Gap Agent generated per-row & aggregate analysis]")
        results_summary.append(("Gap", "PASS", "Per-row gap report & Aggregate gap report generated"))
    else:
        print("\nSTATUS: FAIL [Missing per-row or aggregate gap summary]")
        results_summary.append(("Gap", "FAIL", "Missing gap summaries"))
        sys.exit(1)

    # --------------------------------------------------------------------------
    # SUMMARY TABLE
    # --------------------------------------------------------------------------
    print("\n" + "=" * 80)
    print(" AGENT MULTI-AGENT EXECUTION SUMMARY TABLE")
    print("=" * 80)
    print(f"{'AGENT NAME':<15} | {'STATUS':<6} | {'RESULT SUMMARY'}")
    print("-" * 80)
    for agent_name, status_str, summary_str in results_summary:
        print(f"{agent_name:<15} | {status_str:<6} | {summary_str}")
    print("=" * 80)

if __name__ == "__main__":
    if "--interactive" in sys.argv or "-i" in sys.argv:
        from interactive_cli import main_menu
        main_menu()
    else:
        main()
