import os
import sys
import json
import re

fe_dir = "frontend"

def audit_frontend():
    pages = []
    components = []
    
    # List app routes
    app_dir = os.path.join(fe_dir, "app")
    if os.path.exists(app_dir):
        for root, dirs, files in os.walk(app_dir):
            for file in files:
                if file in ["page.tsx", "page.js", "page.jsx"]:
                    rel_path = os.path.relpath(os.path.join(root, file), app_dir)
                    route_name = "/" if rel_path == "page.tsx" else "/" + os.path.dirname(rel_path).replace("\\", "/")
                    pages.append({
                        "route": route_name,
                        "file": os.path.join(root, file)
                    })
                    
    # List components
    comp_dir = os.path.join(fe_dir, "components")
    if os.path.exists(comp_dir):
        for file in os.listdir(comp_dir):
            if file.endswith((".tsx", ".jsx", ".ts", ".js")):
                components.append(os.path.join(comp_dir, file))
                
    # Scan for mock / hardcoded arrays
    mock_findings = []
    all_fe_files = []
    for root, dirs, files in os.walk(fe_dir):
        if "node_modules" in root or ".next" in root:
            continue
        for file in files:
            if file.endswith((".tsx", ".ts", ".jsx", ".js")):
                filepath = os.path.join(root, file)
                all_fe_files.append(filepath)
                with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                    for idx, line in enumerate(f, 1):
                        if any(k in line.lower() for k in ["mock", "dummy", "sample", "hardcoded"]):
                            mock_findings.append({
                                "file": filepath,
                                "line": idx,
                                "snippet": line.strip()
                            })
                            
    # Detailed analysis per page / component
    page_analysis = {}
    for p in pages:
        with open(p["file"], "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
            page_analysis[p["route"]] = {
                "file": p["file"],
                "has_loading_state": "loading" in content.lower() or "spinner" in content.lower() or "skeleton" in content.lower(),
                "has_error_state": "error" in content.lower() or "catch" in content.lower(),
                "rendered_components": [c for c in components if os.path.basename(c).replace(".tsx", "") in content]
            }

    # Check required pages presence
    required_pages = {
        "dashboard_timeline": False,
        "scout": False,
        "job_detail": False,
        "tracker": False,
        "notifications": False,
        "gap": False,
        "prep": False,
        "profile_import": False,
        "admin_resources_skills_scam": False
    }
    
    # Check routes and components matching these requirements
    routes_str = " ".join([p["route"] for p in pages])
    comps_str = " ".join([os.path.basename(c) for c in components])
    
    # We check page.tsx and modal/view components
    required_pages["dashboard_timeline"] = "/" in [p["route"] for p in pages] or "ActivityFeed" in comps_str
    required_pages["scout"] = "/scout" in routes_str or "Scout" in comps_str
    required_pages["job_detail"] = "/applications" in routes_str or "ApplicationDetail" in comps_str or "KanbanBoard" in comps_str
    required_pages["tracker"] = "/tracker" in routes_str or "KanbanBoard" in comps_str
    required_pages["notifications"] = "Notification" in comps_str or "ActivityFeed" in comps_str
    required_pages["gap"] = "GapReport" in comps_str
    required_pages["prep"] = "Prep" in comps_str
    required_pages["profile_import"] = "/profile" in routes_str or "Profile" in comps_str
    required_pages["admin_resources_skills_scam"] = "/admin" in routes_str or "Admin" in comps_str

    report = {
        "pages_found": pages,
        "components_found": [os.path.basename(c) for c in components],
        "required_pages_audit": required_pages,
        "page_details": page_analysis,
        "mock_findings_count": len(mock_findings),
        "mock_findings": mock_findings
    }
    
    with open("audit_scripts/frontend_report.json", "w") as f:
        json.dump(report, f, indent=2)
        
    print(json.dumps(report, indent=2))

if __name__ == "__main__":
    audit_frontend()
