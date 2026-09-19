import os
import sys
import json
import urllib.request
import urllib.error

sys.path.insert(0, os.path.abspath("."))

def log(msg):
    print(f"[AUDIT-API] {msg}", flush=True)

def audit_wiring_and_api():
    report = {
        "agent_wiring": {},
        "openapi_inventory": {},
        "frontend_api_calls": [],
        "cors_check": {},
        "frontend_api_client_config": {}
    }
    
    # 1. OpenAPI Inventory
    log("Fetching OpenAPI inventory...")
    try:
        req = urllib.request.urlopen("http://127.0.0.1:8000/openapi.json", timeout=3)
        openapi_data = json.loads(req.read().decode('utf-8'))
        paths = openapi_data.get("paths", {})
        inventory = []
        for path, methods in paths.items():
            for method, details in methods.items():
                inventory.append({
                    "method": method.upper(),
                    "path": path,
                    "summary": details.get("summary", ""),
                    "operation_id": details.get("operationId", "")
                })
        report["openapi_inventory"] = {
            "total_endpoints": len(inventory),
            "endpoints": inventory
        }
    except Exception as e:
        report["openapi_inventory"] = {"error": str(e)}

    # 2. CORS Check
    log("Performing CORS check...")
    try:
        req = urllib.request.Request(
            "http://127.0.0.1:8000/health",
            headers={"Origin": "http://localhost:3000"}
        )
        res = urllib.request.urlopen(req, timeout=3)
        headers = dict(res.info())
        report["cors_check"] = {
            "status_code": res.getcode(),
            "allow_origin": headers.get("access-control-allow-origin"),
            "allow_methods": headers.get("access-control-allow-methods"),
            "allow_headers": headers.get("access-control-allow-headers")
        }
    except urllib.error.HTTPError as he:
        headers = dict(he.headers)
        report["cors_check"] = {
            "status_code": he.code,
            "allow_origin": headers.get("access-control-allow-origin")
        }
    except Exception as e:
        report["cors_check"] = {"error": str(e)}

    # 3. Frontend API Calls Scan
    log("Scanning Frontend API calls...")
    frontend_calls = []
    fe_dir = "frontend"
    if os.path.exists(fe_dir):
        for root, dirs, files in os.walk(fe_dir):
            if "node_modules" in root or ".next" in root:
                continue
            for file in files:
                if file.endswith((".ts", ".tsx", ".js", ".jsx")):
                    filepath = os.path.join(root, file)
                    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                        for idx, line in enumerate(f, 1):
                            if "fetch(" in line or "axios" in line or "apiClient" in line or "API_BASE" in line or "http://" in line or "https://" in line:
                                frontend_calls.append({
                                    "file": filepath,
                                    "line": idx,
                                    "snippet": line.strip()
                                })
    report["frontend_api_calls"] = frontend_calls

    # 4. Frontend API Client Config Scan
    log("Checking Frontend API Client config...")
    fe_config = {}
    for p in ["frontend/lib/api.ts", "frontend/utils/api.ts", "frontend/services/api.ts", "frontend/lib/apiClient.ts"]:
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                fe_config[p] = f.read()
    report["frontend_api_client_config"] = fe_config

    with open("audit_scripts/agent_wiring_api_report.json", "w") as f:
        json.dump(report, f, indent=2)

    log("DONE!")

if __name__ == "__main__":
    audit_wiring_and_api()
