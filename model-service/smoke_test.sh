#!/usr/bin/env bash
# ==============================================================================
# Placement Copilot - Model Service Contract Smoke Test
# ==============================================================================
# Verifies that model-service starts up, reaches ready state (/health model_loaded: true),
# and satisfies all API contracts defined in MODEL_SERVICE_CONTRACT.md.
# ==============================================================================

set -e

PORT=8001
BASE_URL="http://127.0.0.1:${PORT}"
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

SPAWNED_PID=""

cleanup() {
    if [ -n "$SPAWNED_PID" ]; then
        echo -e "\n[INFO] Stopping model-service background process (PID: $SPAWNED_PID)..."
        kill "$SPAWNED_PID" 2>/dev/null || true
        wait "$SPAWNED_PID" 2>/dev/null || true
    fi
}
trap cleanup EXIT INT TERM

echo "================================================================================"
echo " Placement Copilot: Model Service Contract Smoke Test"
echo "================================================================================"

# Check if model-service is already running
IS_ALREADY_RUNNING=$("$PYTHON_BIN" -c "
import urllib.request, json, sys
try:
    with urllib.request.urlopen('${BASE_URL}/health', timeout=2) as resp:
        data = json.loads(resp.read().decode())
        if data.get('status') == 'ok' and data.get('model_loaded') is True:
            sys.stdout.write('1')
            sys.exit(0)
except Exception:
    pass
sys.stdout.write('0')
" 2>/dev/null | tr -d '\r\n')

if [ "$IS_ALREADY_RUNNING" = "1" ]; then
    echo "[INFO] Detected existing healthy model-service process running at ${BASE_URL}."
else
    echo "[INFO] Starting model-service on port ${PORT}..."
    cd "$SCRIPT_DIR"
    "$PYTHON_BIN" main.py > model-service.log 2>&1 &
    SPAWNED_PID=$!
    echo "[INFO] Started process PID: $SPAWNED_PID (logging to model-service.log)"
fi

# Wait for /health model_loaded == true
echo "[INFO] Waiting for service health check (model_loaded: true)..."
MAX_ATTEMPTS=45
ATTEMPT=0
READY=0

while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
    ATTEMPT=$((ATTEMPT + 1))
    IS_READY=$("$PYTHON_BIN" -c "
import urllib.request, json, sys
try:
    with urllib.request.urlopen('${BASE_URL}/health', timeout=2) as resp:
        data = json.loads(resp.read().decode())
        if data.get('status') == 'ok' and data.get('model_loaded') is True:
            sys.stdout.write('1')
            sys.exit(0)
except Exception:
    pass
sys.stdout.write('0')
" 2>/dev/null | tr -d '\r\n')

    if [ "$IS_READY" = "1" ]; then
        READY=1
        echo "[SUCCESS] Service is ready and models loaded after ${ATTEMPT}s."
        break
    fi
    sleep 1
done

if [ $READY -ne 1 ]; then
    echo "[FAIL] Service failed to reach ready state within ${MAX_ATTEMPTS} seconds."
    if [ -f "model-service.log" ]; then
        echo "--- model-service.log ---"
        tail -n 20 model-service.log
    fi
    exit 1
fi

echo "--------------------------------------------------------------------------------"
echo " Running Contract Validation Tests..."
echo "--------------------------------------------------------------------------------"

TOTAL_TESTS=0
PASSED_TESTS=0

run_test() {
    local test_name="$1"
    local method="$2"
    local endpoint="$3"
    local payload="$4"
    local validation_python="$5"

    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    echo -n "Test ${TOTAL_TESTS}: [${method} ${endpoint}] ${test_name} ... "

    VALID=$(printf "%s" "$payload" | VALID_CODE="$validation_python" "$PYTHON_BIN" -c "
import os, sys, urllib.request, urllib.error, json

url = '${BASE_URL}${endpoint}'
method = '${method}'
payload_raw = sys.stdin.read().strip()

headers = {'Content-Type': 'application/json'} if method == 'POST' else {}
data_bytes = payload_raw.encode('utf-8') if (method == 'POST' and payload_raw) else None

req = urllib.request.Request(url, data=data_bytes, headers=headers, method=method)

try:
    with urllib.request.urlopen(req, timeout=15) as resp:
        if resp.status != 200:
            sys.stdout.write(f'FAIL (HTTP {resp.status})')
            sys.exit(0)
        body = resp.read().decode('utf-8')
        data = json.loads(body)
        code = os.environ.get('VALID_CODE', '')
        exec(code, {'data': data, 'isinstance': isinstance, 'len': len, 'str': str, 'int': int, 'float': float, 'bool': bool})
        sys.stdout.write('PASS')
except urllib.error.HTTPError as e:
    err_body = e.read().decode('utf-8') if e.fp else ''
    sys.stdout.write(f'FAIL (HTTP {e.code}: {err_body})')
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

# 1. Health Check
run_test "Health Status Verification" "GET" "/health" "" "
assert data.get('status') == 'ok'
assert data.get('model_loaded') is True
"

# 2. Embeddings Endpoint
EMBED_PAYLOAD='{"texts": ["Built a drone orthomosaic detection pipeline using GeoTIFF and rasterio.", "Looking for an intern experienced in object detection and satellite imagery."]}'
run_test "Embeddings Vector Output (/embed)" "POST" "/embed" "$EMBED_PAYLOAD" "
assert data.get('model_name') == 'all-MiniLM-L6-v2'
assert data.get('dimension') == 384
assert len(data.get('embeddings', [])) == 2
assert len(data['embeddings'][0]) == 384
assert len(data['embeddings'][1]) == 384
"

# 3. LLM Generate - Scam Explanation
SCAM_PAYLOAD='{"task_type": "scam_explanation", "context": {"flagged_reasons": ["sender domain does not match official domain", "requests upfront processing fee"], "recruiter_info": {"claimed_company": "TechNova Solutions", "email_domain": "technova-careers.in"}}}'
run_test "LLM Generate: Scam Explanation" "POST" "/llm-generate" "$SCAM_PAYLOAD" "
assert data.get('task_type') == 'scam_explanation'
assert isinstance(data.get('generated_text'), str) and len(data['generated_text']) > 0
"

# 4. LLM Generate - Prep Recommendations
PREP_PAYLOAD='{"task_type": "prep_recommendations", "context": {"jd_summary": "Python and Docker engineer needed.", "candidates": [{"id": 1, "title": "Docker Crash Course", "skills": ["docker"]}]}}'
run_test "LLM Generate: Prep Recommendations" "POST" "/llm-generate" "$PREP_PAYLOAD" "
assert data.get('task_type') == 'prep_recommendations'
assert isinstance(data.get('generated_text'), str)
"

# 5. LLM Generate - Gap Summary
GAP_PAYLOAD='{"task_type": "gap_summary", "context": {"rejected_applications": [{"role_tag": "SDE", "rejection_stage": "OA"}, {"role_tag": "SDE", "rejection_stage": "OA"}, {"role_tag": "CV", "rejection_stage": "INTERVIEW"}]}}'
run_test "LLM Generate: Gap Summary" "POST" "/llm-generate" "$GAP_PAYLOAD" "
assert data.get('task_type') == 'gap_summary'
assert isinstance(data.get('generated_text'), str) and len(data['generated_text']) > 0
"

echo "================================================================================"
if [ $PASSED_TESTS -eq $TOTAL_TESTS ]; then
    echo "[SUCCESS] All ${PASSED_TESTS}/${TOTAL_TESTS} Contract Smoke Tests PASSED!"
    echo "================================================================================"
    exit 0
else
    echo "[FAIL] ${PASSED_TESTS}/${TOTAL_TESTS} Contract Smoke Tests Passed."
    echo "================================================================================"
    exit 1
fi
