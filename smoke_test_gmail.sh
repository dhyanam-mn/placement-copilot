#!/usr/bin/env bash
# ==============================================================================
# Placement Copilot — Gmail Tracker Agent Live Smoke Test
# ==============================================================================
# Verifies that backend server and Gmail Tracker Agent endpoint POST /tracker/gmail/sync
# process mock email fixtures, perform classification & company fuzzy matching,
# update application status with status_source="gmail_auto", and trigger per-row gap reports.
# ==============================================================================

set -e

BACKEND_PORT=8000
BACKEND_URL="http://127.0.0.1:${BACKEND_PORT}"

MODEL_SERVICE_PORT=8001
MODEL_SERVICE_URL="http://127.0.0.1:${MODEL_SERVICE_PORT}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Detect python executable
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
echo " Placement Copilot: Gmail Tracker Agent Live Smoke Test"
echo "================================================================================"

# 0. Start model-service on port 8001 if not running
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

# 1. Start backend main.py on port 8000 if not running
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

# 2. Wait for model-service model_loaded == true
echo "[INFO] Waiting for model-service..."
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

# 3. Wait for backend server
echo "[INFO] Waiting for backend server..."
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
    exit 1
fi

echo "--------------------------------------------------------------------------------"
echo " Running Gmail Tracker Agent Live Mock Verification Tests..."
echo "--------------------------------------------------------------------------------"

# Test 1: Check GET /tracker/gmail/status
echo -n "Test 1: [GET /tracker/gmail/status] Check Tracker Status ... "
STATUS_RES=$("$PYTHON_BIN" -c "
import urllib.request, json
req = urllib.request.Request('${BACKEND_URL}/tracker/gmail/status')
with urllib.request.urlopen(req) as resp:
    data = json.loads(resp.read().decode())
    assert 'is_authenticated' in data
    assert 'sync_state' in data
    print('PASS')
")
echo "$STATUS_RES"

# Test 2: Trigger POST /tracker/gmail/sync with Mock Fixtures
echo -n "Test 2: [POST /tracker/gmail/sync] Process Mock Email Fixtures ... "

SYNC_PAYLOAD='{
  "mock_messages": [
    {
      "id": "mock_dronamaps_01",
      "history_id": "9001",
      "sender": "careers@dronamaps.com",
      "subject": "Invitation to Online Assessment - DronaMaps CV Intern",
      "body": "Please complete your coding assessment on HackerRank within 48 hours."
    },
    {
      "id": "mock_razorpay_02",
      "history_id": "9002",
      "sender": "recruiter@razorpay.com",
      "subject": "Update on your application at Razorpay",
      "body": "Thank you for applying to Razorpay. Unfortunately, we have decided to move forward with other candidates."
    }
  ]
}'

SYNC_RES=$(printf "%s" "$SYNC_PAYLOAD" | "$PYTHON_BIN" -c "
import sys, urllib.request, json
url = '${BACKEND_URL}/tracker/gmail/sync'
payload = sys.stdin.read().encode('utf-8')
headers = {'Content-Type': 'application/json'}
req = urllib.request.Request(url, data=payload, headers=headers, method='POST')

with urllib.request.urlopen(req) as resp:
    data = json.loads(resp.read().decode())
    assert data.get('status') == 'success'
    assert data.get('messages_classified_and_matched') >= 2
    print('PASS')
")
echo "$SYNC_RES"

# Test 3: Verify Status Update & Gap Report Triggering on Razorpay row
echo -n "Test 3: [GET /applications/2] Verify Razorpay REJECTED Status & Auto Gap Report ... "
VERIFY_RES=$("$PYTHON_BIN" -c "
import urllib.request, json
req = urllib.request.Request('${BACKEND_URL}/applications/2')
with urllib.request.urlopen(req) as resp:
    data = json.loads(resp.read().decode())
    assert data.get('status') == 'REJECTED'
    assert data.get('status_source') == 'gmail_auto'
    assert data.get('gap_report_id') is not None
    print('PASS')
")
echo "$VERIFY_RES"

echo "================================================================================"
echo "[SUCCESS] All Gmail Tracker Agent Live Smoke Tests PASSED!"
echo "================================================================================"
