import os
import sys
import json
import re

terms = [
    "student_skills",
    "RESOURCE_DATABASE",
    "RED_FLAG_PHRASES",
    "LOOKALIKE_INDICATORS",
    "PUBLIC_EMAIL_DOMAINS",
    "base_resume.json",
    "base_resume.tex",
    "gmail_sync_state.json",
    "SerpAPI",
    "Celery",
    "Glassdoor",
    "question-bank",
    "answer-feedback"
]

def search_terms():
    results = {}
    for term in terms:
        term_matches = []
        for root, dirs, files in os.walk("."):
            if ".git" in root or "__pycache__" in root or "node_modules" in root or ".next" in root or "audit_scripts" in root:
                continue
            for file in files:
                if file.endswith((".py", ".ts", ".tsx", ".json", ".md", ".env", ".sh")):
                    filepath = os.path.join(root, file)
                    try:
                        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                            for idx, line in enumerate(f, 1):
                                if term.lower() in line.lower():
                                    term_matches.append({
                                        "file": filepath,
                                        "line": idx,
                                        "content": line.strip()
                                    })
                    except Exception:
                        pass
        results[term] = term_matches
        
    with open("audit_scripts/hardcoding_report.json", "w") as f:
        json.dump(results, f, indent=2)
        
    print(json.dumps(results, indent=2))

if __name__ == "__main__":
    search_terms()
