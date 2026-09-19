import os
import sys
import time
import json
import urllib.request
import urllib.error
import subprocess

sys.path.insert(0, os.path.abspath("."))

def log(msg):
    print(f"[AUDIT-SERVICES] {msg}", flush=True)

results = {}

# 1. Database Connection & Source
log("Checking Postgres...")
try:
    from database import engine, DATABASE_URL
    import sqlalchemy
    with engine.connect() as conn:
        res = conn.execute(sqlalchemy.text("SELECT version();")).fetchone()
        db_ver = res[0] if res else "Unknown"
    
    masked_url = DATABASE_URL
    if "@" in masked_url:
        proto_user, host_db = masked_url.split("@", 1)
        proto = proto_user.split(":")[0]
        user = proto_user.split("//")[-1].split(":")[0]
        masked_url = f"{proto}://{user}:****@{host_db}"
        
    results["postgres"] = {
        "status": "REACHABLE",
        "version": db_ver,
        "connection_string_source": f"database.py / env (URL: {masked_url})"
    }
except Exception as e:
    results["postgres"] = {"status": "FAILED", "error": str(e)}
log(f"Postgres result: {results['postgres']}")

# 2. FastAPI :8000
log("Checking FastAPI :8000...")
try:
    req = urllib.request.urlopen("http://localhost:8000/openapi.json", timeout=2)
    data = json.loads(req.read().decode('utf-8'))
    results["fastapi"] = {
        "status": "UP",
        "info": f"openapi.json fetched successfully, title: {data.get('info', {}).get('title')}, paths count: {len(data.get('paths', {}))}"
    }
except Exception as e:
    results["fastapi"] = {"status": "DOWN / UNREACHABLE", "error": str(e)}
log(f"FastAPI result: {results['fastapi']}")

# 3. Model-service :8001
log("Checking Model Service :8001...")
try:
    payload = json.dumps({"texts": ["audit smoke test"]}).encode('utf-8')
    req = urllib.request.Request("http://localhost:8001/embed", data=payload, headers={'Content-Type': 'application/json'})
    res = urllib.request.urlopen(req, timeout=2)
    res_data = json.loads(res.read().decode('utf-8'))
    embeddings = res_data.get("embeddings", [])
    dim = len(embeddings[0]) if embeddings else 0
    results["model_service"] = {
        "status": "UP",
        "response": f"Embeddings returned for 1 text, dimension: {dim}"
    }
except Exception as e:
    results["model_service"] = {"status": "DOWN / UNREACHABLE", "error": str(e)}
log(f"Model-service result: {results['model_service']}")

# 4. Ollama :11434
log("Checking Ollama :11434...")
try:
    tags_req = urllib.request.urlopen("http://localhost:11434/api/tags", timeout=2)
    tags_data = json.loads(tags_req.read().decode('utf-8'))
    models = [m.get("name") for m in tags_data.get("models", [])]
    llama31_installed = any("llama3.1" in m for m in models)
    
    t0 = time.time()
    gen_payload = json.dumps({"model": "llama3.1:8b", "prompt": "Hi", "stream": False}).encode('utf-8')
    gen_req = urllib.request.Request("http://localhost:11434/api/generate", data=gen_payload, headers={'Content-Type': 'application/json'})
    gen_res = urllib.request.urlopen(gen_req, timeout=5)
    gen_data = json.loads(gen_res.read().decode('utf-8'))
    elapsed = time.time() - t0
    
    results["ollama"] = {
        "status": "UP",
        "installed_models": models,
        "llama3.1_8b_installed": llama31_installed,
        "tiny_generate_response": gen_data.get("response", "").strip(),
        "timing_seconds": round(elapsed, 3)
    }
except Exception as e:
    results["ollama"] = {"status": "DOWN / UNREACHABLE", "error": str(e)}
log(f"Ollama result: {results['ollama']}")

# 5. Gmail Token & API call
log("Checking Gmail token...")
try:
    token_exists = os.path.exists("token.json")
    gmail_info = {"token_json_exists": token_exists}
    if token_exists:
        try:
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build
            creds = Credentials.from_authorized_user_file('token.json')
            gmail_info["valid"] = creds.valid
            gmail_info["expired"] = creds.expired
            gmail_info["refresh_token_present"] = bool(creds.refresh_token)
            
            service = build('gmail', 'v1', credentials=creds)
            res = service.users().messages().list(userId='me', maxResults=1).execute()
            gmail_info["api_call_status"] = "SUCCESS"
            gmail_info["messages_result_keys"] = list(res.keys())
        except Exception as ge:
            gmail_info["api_call_status"] = f"FAILED: {ge}"
    results["gmail"] = gmail_info
except Exception as e:
    results["gmail"] = {"status": "FAILED", "error": str(e)}
log(f"Gmail result: {results['gmail']}")

# 6. Tectonic
log("Checking Tectonic...")
try:
    proc = subprocess.run(["tectonic", "--version"], capture_output=True, text=True)
    if proc.returncode == 0:
        ver = proc.stdout.strip().splitlines()[0]
        tex_file = "audit_scripts/sample_test.tex"
        with open(tex_file, "w") as f:
            f.write(r"\documentclass{article}\begin{document}Audit Test\end{document}")
        compile_proc = subprocess.run(["tectonic", tex_file], capture_output=True, text=True)
        pdf_created = os.path.exists("audit_scripts/sample_test.pdf")
        if pdf_created:
            os.remove("audit_scripts/sample_test.pdf")
        if os.path.exists(tex_file):
            os.remove(tex_file)
        results["tectonic"] = {
            "status": "INSTALLED & WORKING" if pdf_created else "INSTALLED BUT COMPILE FAILED",
            "version": ver,
            "pdf_generated": pdf_created,
            "compile_stderr": compile_proc.stderr[:200]
        }
    else:
        results["tectonic"] = {"status": "NOT FOUND", "error": proc.stderr}
except Exception as e:
    results["tectonic"] = {"status": "NOT FOUND / ERROR", "error": str(e)}
log(f"Tectonic result: {results['tectonic']}")

# 7. Env Vars Check
log("Checking Env Vars...")
env_vars = {
    "DATABASE_URL": bool(os.environ.get("DATABASE_URL")),
    "ADZUNA_APP_ID": bool(os.environ.get("ADZUNA_APP_ID")),
    "ADZUNA_APP_KEY": bool(os.environ.get("ADZUNA_APP_KEY")),
    "MODEL_SERVICE_URL": os.environ.get("MODEL_SERVICE_URL", "not set (default: http://localhost:8001)"),
    "OLLAMA_URL": os.environ.get("OLLAMA_URL", "not set (default: http://localhost:11434)"),
    "NEXT_PUBLIC_API_BASE_URL": os.environ.get("NEXT_PUBLIC_API_BASE_URL", "not set"),
}
results["env_vars"] = env_vars

log("DONE!")
with open("audit_scripts/services_report.json", "w") as f:
    json.dump(results, f, indent=2)
print(json.dumps(results, indent=2))
