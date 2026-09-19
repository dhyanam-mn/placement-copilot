#!/usr/bin/env bash
# ==============================================================================
# Placement Copilot - Backend API Contract Live Smoke Test
# ==============================================================================
# Verifies that backend server starts up on port 8000, connects to live PostgreSQL,
# and satisfies all 10 API contracts defined in API_CONTRACT.md.
# ==============================================================================

set -e

BACKEND_PORT=8000
BACKEND_URL="http://127.0.0.1:${BACKEND_PORT}"

MODEL_SERVICE_PORT=8001
MODEL_SERVICE_URL="http://127.0.0.1:${MODEL_SERVICE_PORT}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Detect python executable (preferring python environment with fastapi installed)
PYTHON_BIN=""
for cand in python python3 py python.exe python3.exe "/c/Program Files/Python311/python.exe"; do
    if command -v "$cand" &>/dev/null && "$cand" -c "import fastapi" &>/dev/null; then
        PYTHON_BIN="$cand"
        break
    fi
done

if [ -z "$PYTHON_BIN" ]; then
    if command -v python &>/dev/null; then
        PYTHON_BIN="python"
    elif command -v python3 &>/dev/null; then
        PYTHON_BIN="python3"
    else
        echo "[ERROR] Python executable not found in PATH!"
        exit 1
    fi
fi

echo "[INFO] Using Python: $($PYTHON_BIN -c 'import sys; print(sys.executable)')"

MODEL_PID=""
BACKEND_PID=""

cleanup() {
    echo -e "\n[INFO] Cleaning up background processes..."
    if [ -n "$BACKEND_PID" ]; then
        echo "[INFO] Stopping backend process (PID: $BACKEND_PID)..."
        kill "$BACKEND_PID" 2>/dev/null || true
        wait "$BACKEND_PID" 2>/dev/null || true
    fi
    if [ -n "$MODEL_PID" ]; then
        echo "[INFO] Stopping model-service process (PID: $MODEL_PID)..."
        kill "$MODEL_PID" 2>/dev/null || true
        wait "$MODEL_PID" 2>/dev/null || true
    fi
}
trap cleanup EXIT INT TERM

echo "================================================================================"
echo " Placement Copilot: Full Backend Live Smoke Test"
echo "================================================================================"

# 0. Database Connection & Seed Row Audit
"$PYTHON_BIN" -c "
import os
from database import DATABASE_URL, SessionLocal
from models import Application

# Mask credentials for printing
masked_url = DATABASE_URL
if '@' in masked_url:
    prefix, rest = masked_url.split('://', 1)
    creds, host = rest.split('@', 1)
    user = creds.split(':', 1)[0] if ':' in creds else creds
    masked_url = f'{prefix}://{user}:****@{host}'

print(f'[INFO] Connecting to DATABASE_URL: {masked_url}')
db = SessionLocal()
count = db.query(Application).count()
print(f'[SUCCESS] Verified connection to live PostgreSQL database schema. Found {count} applications (including seed rows).')
db.close()
"

# 1. Start model-service on port 8001 if not running
if "$PYTHON_BIN" -c "
import urllib.request, json, sys
try:
    with urllib.request.urlopen('${MODEL_SERVICE_URL}/health', timeout=2) as resp:
        data = json.loads(resp.read().decode())
        if data.get('status') == 'ok' and data.get('model_loaded') is True:
            sys.exit(0)
except Exception:
    pass
sys.exit(1)
" &>/dev/null; then
    echo "[INFO] Detected active model-service at ${MODEL_SERVICE_URL}."
else
    echo "[INFO] Starting model-service on port ${MODEL_SERVICE_PORT}..."
    cd "$SCRIPT_DIR/model-service"
    "$PYTHON_BIN" main.py > model-service-smoke.log 2>&1 &
    MODEL_PID=$!
    cd "$SCRIPT_DIR"
    echo "[INFO] Started model-service (PID: $MODEL_PID)"
fi

# 2. Start backend main.py on port 8000 if not running
if "$PYTHON_BIN" -c "
import urllib.request, json, sys
try:
    with urllib.request.urlopen('${BACKEND_URL}/health', timeout=2) as resp:
        sys.exit(0)
except Exception:
    pass
sys.exit(1)
" &>/dev/null; then
    echo "[INFO] Detected active backend server at ${BACKEND_URL}."
else
    echo "[INFO] Starting backend server on port ${BACKEND_PORT}..."
    cd "$SCRIPT_DIR"
    "$PYTHON_BIN" main.py > backend-smoke.log 2>&1 &
    BACKEND_PID=$!
    echo "[INFO] Started backend server (PID: $BACKEND_PID)"
fi

# 3. Wait for model-service model_loaded == true
echo "[INFO] Waiting for model-service (model_loaded: true)..."
MAX_ATTEMPTS=45
ATTEMPT=0
MODEL_READY=0

while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
    ATTEMPT=$((ATTEMPT + 1))
    IS_READY=$("$PYTHON_BIN" -c "
import urllib.request, json, sys
try:
    with urllib.request.urlopen('${MODEL_SERVICE_URL}/health', timeout=2) as resp:
        data = json.loads(resp.read().decode())
        if data.get('status') == 'ok' and data.get('model_loaded') is True:
            sys.stdout.write('1')
            sys.exit(0)
except Exception:
    pass
sys.stdout.write('0')
" 2>/dev/null | tr -d '\r\n')

    if [ "$IS_READY" = "1" ]; then
        MODEL_READY=1
        echo "[SUCCESS] model-service is ready after ${ATTEMPT}s."
        break
    fi
    sleep 1
done

if [ $MODEL_READY -ne 1 ]; then
    echo "[FAIL] model-service failed to reach ready state within ${MAX_ATTEMPTS} seconds."
    exit 1
fi

# 4. Wait for backend server to respond
echo "[INFO] Waiting for backend server to respond..."
ATTEMPT=0
READY=0

while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
    ATTEMPT=$((ATTEMPT + 1))
    IS_READY=$("$PYTHON_BIN" -c "
import urllib.request, json, sys
try:
    with urllib.request.urlopen('${BACKEND_URL}/health', timeout=2) as resp:
        if resp.status == 200:
            sys.stdout.write('1')
            sys.exit(0)
except Exception:
    pass
sys.stdout.write('0')
" 2>/dev/null | tr -d '\r\n')

    if [ "$IS_READY" = "1" ]; then
        READY=1
        echo "[SUCCESS] Backend server is ready after ${ATTEMPT}s."
        break
    fi
    sleep 1
done

if [ $READY -ne 1 ]; then
    echo "[FAIL] Backend server failed to respond within ${MAX_ATTEMPTS} seconds."
    if [ -f "backend-smoke.log" ]; then
        echo "--- backend-smoke.log ---"
        tail -n 25 backend-smoke.log
    fi
    exit 1
fi

echo "--------------------------------------------------------------------------------"
echo " Running API Contract Live Route Verification Tests..."
echo "--------------------------------------------------------------------------------"

TOTAL_TESTS=0
PASSED_TESTS=0

run_test() {
    local test_name="$1"
    local method="$2"
    local endpoint="$3"
    local payload="$4"
    local validation_python="$5"
    local expected_code="${6:-200}"

    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    echo -n "Test ${TOTAL_TESTS}: [${method} ${endpoint}] ${test_name} ... "

    VALID=$(printf "%s" "$payload" | VALID_CODE="$validation_python" "$PYTHON_BIN" -c "
import os, sys, urllib.request, urllib.error, json

url = '${BACKEND_URL}${endpoint}'
method = '${method}'
payload_str = sys.stdin.read().strip()
expected_status = int('${expected_code}')

headers = {'Content-Type': 'application/json'} if method in ('POST', 'PATCH') else {}
data_bytes = payload_str.encode('utf-8') if (method in ('POST', 'PATCH') and payload_str) else None

req = urllib.request.Request(url, data=data_bytes, headers=headers, method=method)

try:
    with urllib.request.urlopen(req, timeout=20) as resp:
        if resp.status != expected_status:
            sys.stdout.write(f'FAIL (Expected HTTP {expected_status}, got {resp.status})')
            sys.exit(0)
        body = resp.read().decode('utf-8')
        data = json.loads(body)
        code = os.environ.get('VALID_CODE', '')
        exec(code, {'data': data, 'isinstance': isinstance, 'len': len, 'str': str, 'int': int, 'float': float, 'bool': bool})
        sys.stdout.write('PASS')
except urllib.error.HTTPError as e:
    body = e.read().decode('utf-8') if e.fp else '{}'
    if e.code == expected_status:
        try:
            data = json.loads(body)
            code = os.environ.get('VALID_CODE', '')
            exec(code, {'data': data, 'isinstance': isinstance, 'len': len, 'str': str, 'int': int, 'float': float, 'bool': bool})
            sys.stdout.write('PASS')
        except Exception as ex:
            sys.stdout.write(f'FAIL (Validation error: {ex})')
    else:
        sys.stdout.write(f'FAIL (HTTP {e.code}: {body})')
except Exception as e:
    sys.stdout.write(f'FAIL ({e})')
" 2>/dev/null | tr -d '\r\n')

    if [ "$VALID" = "PASS" ]; then
        echo "PASS"
        PASSED_TESTS=$((PASSED_TESTS + 1))
    else
        echo "$VALID"
    fi
}

# 1. GET /applications
run_test "List Applications (GET /applications)" "GET" "/applications" "" "
assert 'applications' in data
assert isinstance(data['applications'], list)
assert len(data['applications']) > 0
app = data['applications'][0]
assert 'id' in app and 'company' in app and 'status' in app
"

# 2. GET /applications?status=INTERVIEW
run_test "Filter Applications by Status (GET /applications?status=INTERVIEW)" "GET" "/applications?status=INTERVIEW" "" "
assert 'applications' in data
assert isinstance(data['applications'], list)
for app in data['applications']:
    assert app['status'] == 'INTERVIEW'
"

# 3. GET /applications/{id}
run_test "Get Single Application Detail (GET /applications/1)" "GET" "/applications/1" "" "
assert data.get('id') == 1
assert 'company' in data
assert 'role' in data
assert 'status' in data
"

# 4. POST /applications (Scout Agent Entry)
CREATE_PAYLOAD='{"company": "Innovaccer Test", "role": "SDE-1", "jd_text": "Strong DSA fundamentals, system design basics, SQL", "source": "adzuna"}'
run_test "Create Application / Scout Embed Match (POST /applications)" "POST" "/applications" "$CREATE_PAYLOAD" "
assert 'id' in data
assert data['company'] == 'Innovaccer Test'
assert data['status'] == 'DISCOVERED'
assert isinstance(data.get('match_score'), (int, float))
" 201

# 5. POST /applications/{id}/tailor
run_test "Tailor Resume Reordering (POST /applications/1/tailor)" "POST" "/applications/1/tailor" "" "
assert 'tailored_resume_id' in data
assert 'resume_data' in data
assert 'ordered_bullets' in data['resume_data']
"

# 6. PATCH /applications/{id}/status (Auto Gap Report Trigger)
PATCH_PAYLOAD='{"status": "GHOSTED", "status_source": "auto_ghost"}'
run_test "Update Status & Trigger Gap Report (PATCH /applications/3/status)" "PATCH" "/applications/3/status" "$PATCH_PAYLOAD" "
assert data.get('id') == 3
assert data.get('status') == 'GHOSTED'
assert data.get('status_source') == 'auto_ghost'
assert data.get('gap_report_id') is not None
"

# 7. GET /applications/{id}/gap-report
run_test "Get Per-Row Gap Report (GET /applications/3/gap-report)" "GET" "/applications/3/gap-report" "" "
assert data.get('application_id') == 3
assert data.get('report_type') == 'per_row'
assert 'summary_text' in data
assert 'details' in data
"

# 8. POST /applications/{id}/gap-report
run_test "Generate Per-Row Gap Report (POST /applications/4/gap-report)" "POST" "/applications/4/gap-report" "" "
assert data.get('application_id') == 4
assert data.get('report_type') == 'per_row'
assert isinstance(data.get('summary_text'), str)
"

# 9. GET /gap-report
run_test "Get Aggregate Gap Report (GET /gap-report)" "GET" "/gap-report" "" "
assert data.get('report_type') == 'aggregate'
assert 'summary_text' in data
assert 'details' in data
"

# 10. POST /applications/{id}/scam-check
SCAM_PAYLOAD='{"recruiter_name": "Rohan Sharma", "recruiter_domain": "technova-careers.in", "claimed_company": "TechNova Solutions"}'
run_test "Run Scam Check (POST /applications/1/scam-check)" "POST" "/applications/1/scam-check" "$SCAM_PAYLOAD" "
assert 'id' in data
assert isinstance(data.get('risk_score'), (int, float))
assert isinstance(data.get('flagged_reasons'), list)
"

# 11. GET /applications/{id}/prep
run_test "Prep Recommendations (GET /applications/1/prep)" "GET" "/applications/1/prep" "" "
assert data.get('application_id') == 1
assert isinstance(data.get('recommendations'), list)
"

# 12. Error Test: 404 Not Found
run_test "Error Shape: 404 Not Found (GET /applications/999999)" "GET" "/applications/999999" "" "
assert data.get('error') == 'not_found'
assert 'does not exist' in data.get('detail', '')
" 404

# 13. Error Test: 422 Validation Error
INVALID_STATUS_PAYLOAD='{"status": "INVALID_STATUS"}'
run_test "Error Shape: 422 Validation Error (PATCH /applications/1/status)" "PATCH" "/applications/1/status" "$INVALID_STATUS_PAYLOAD" "
assert data.get('error') == 'validation_error'
" 422

echo "================================================================================"
if [ $PASSED_TESTS -eq $TOTAL_TESTS ]; then
    echo "[SUCCESS] All ${PASSED_TESTS}/${TOTAL_TESTS} Backend API Live Route Tests PASSED!"
    echo "================================================================================"
    exit 0
else
    echo "[FAIL] ${PASSED_TESTS}/${TOTAL_TESTS} Backend API Live Route Tests Passed."
    echo "================================================================================"
    exit 1
fi
