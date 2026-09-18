# Model Service

FastAPI microservice implementing the specifications defined in [`MODEL_SERVICE_CONTRACT.md`](../MODEL_SERVICE_CONTRACT.md).

This service runs on port `8001` and provides embedding generation and LLM text generation endpoints consumed by the FastAPI backend.

Currently implemented with **placeholder logic** matching the contract schemas exactly, allowing full backend and client integration testing with `curl` before wiring in `sentence-transformers` and local Ollama models.

---

## Getting Started

### 1. Install Dependencies

From the `model-service` directory:

```bash
pip install -r requirements.txt
```

### 2. Run the Service

Run with `uvicorn` on port **8001**:

```bash
uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

Or run directly via Python:

```bash
python main.py
```

The service will be live at `http://localhost:8001`.
Interactive Swagger API docs are available at `http://localhost:8001/docs`.

> **Note for Windows PowerShell Users:**
> In PowerShell, use `curl.exe` instead of `curl` (which is an alias to `Invoke-WebRequest`), or use Git Bash / WSL. When passing JSON with `curl.exe` in PowerShell, escape internal double quotes as `\"` or use single-quoted strings:
> ```powershell
> curl.exe -X POST http://localhost:8001/embed -H "Content-Type: application/json" --data '{\"texts\": [\"Hello world\"]}'
> ```

---

## Endpoint Testing with `curl`

### 1. Health Check (`GET /health`)

Check whether the service is running and models are ready.

```bash
curl -X GET "http://localhost:8001/health" -H "Accept: application/json"
```

**Expected Response (HTTP 200):**
```json
{
  "status": "ok",
  "model_loaded": true
}
```

---

### 2. Embeddings (`POST /embed`)

Generate 384-dimensional embeddings for a batch of strings (1–50 items).

```bash
curl -X POST "http://localhost:8001/embed" \
  -H "Content-Type: application/json" \
  -d '{
    "texts": [
      "Built a drone orthomosaic detection pipeline using GeoTIFF and rasterio.",
      "Looking for an intern experienced in object detection and satellite imagery."
    ]
  }'
```

**Expected Response (HTTP 200):**
```json
{
  "embeddings": [
    [0.0123, -0.0456, "... 384 floats total"],
    [0.0201, -0.0333, "... 384 floats total"]
  ],
  "model_name": "all-MiniLM-L6-v2",
  "dimension": 384
}
```

#### Error Case: Empty String in texts

```bash
curl -i -X POST "http://localhost:8001/embed" \
  -H "Content-Type: application/json" \
  -d '{
    "texts": [
      "Valid bullet point",
      ""
    ]
  }'
```

**Expected Response (HTTP 400):**
```json
{
  "error": "empty_string",
  "detail": "texts[1] is empty"
}
```

#### Error Case: Exceeding 50 Items

```bash
curl -i -X POST "http://localhost:8001/embed" \
  -H "Content-Type: application/json" \
  -d '{
    "texts": '"$(python -c 'import json; print(json.dumps(["item"] * 55))"')"'
  }'
```

**Expected Response (HTTP 400):**
```json
{
  "error": "too_many_texts",
  "detail": "max 50 texts per request, got 55"
}
```

---

### 3. LLM Generation (`POST /llm-generate`)

Supports the 3 specific system generation tasks.

#### A. Task: `scam_explanation`

Explains why an application email was flagged by the rule engine.

```bash
curl -X POST "http://localhost:8001/llm-generate" \
  -H "Content-Type: application/json" \
  -d '{
    "task_type": "scam_explanation",
    "context": {
      "flagged_reasons": [
        "sender domain does not match company'\''s official domain",
        "requests processing fee before interview"
      ],
      "recruiter_info": {
        "name": "Rohan Sharma",
        "claimed_company": "TechNova Solutions",
        "email_domain": "technova-careers.in"
      }
    }
  }'
```

**Expected Response (HTTP 200):**
```json
{
  "generated_text": "This looks risky: sender domain does not match company's official domain, and requests processing fee before interview. Exercise caution before sharing personal data or proceeding with TechNova Solutions.",
  "task_type": "scam_explanation",
  "error": null
}
```

#### B. Task: `answer_feedback`

Constructs qualitative feedback for mock interview answers.

```bash
curl -X POST "http://localhost:8001/llm-generate" \
  -H "Content-Type: application/json" \
  -d '{
    "task_type": "answer_feedback",
    "context": {
      "question": "Walk me through your approach to hard-negative mining in the DronaMaps pipeline.",
      "student_answer": "I used sliding window tiling and filtered false positives based on confidence thresholds.",
      "expected_topics": [
        "hard negative mining",
        "sliding window tiling",
        "confidence thresholding"
      ]
    }
  }'
```

**Expected Response (HTTP 200):**
```json
{
  "generated_text": "Good coverage of key concepts — you explained your approach clearly. To strengthen your answer, explicitly emphasize 'hard negative mining' directly.",
  "task_type": "answer_feedback",
  "error": null
}
```

#### C. Task: `gap_summary`

Summarizes application rejection patterns.

```bash
curl -X POST "http://localhost:8001/llm-generate" \
  -H "Content-Type: application/json" \
  -d '{
    "task_type": "gap_summary",
    "context": {
      "rejected_applications": [
        { "role_tag": "SDE", "rejection_stage": "OA" },
        { "role_tag": "SDE", "rejection_stage": "OA" },
        { "role_tag": "SDE", "rejection_stage": "INTERVIEW" },
        { "role_tag": "CV", "rejection_stage": "INTERVIEW" }
      ]
    }
  }'
```

**Expected Response (HTTP 200):**
```json
{
  "generated_text": "You are consistently advancing past resume screening but facing bottlenecks during technical assessments for CV/SDE roles.",
  "task_type": "gap_summary",
  "error": null
}
```

---

### 4. Prep Evaluation (`POST /prep/evaluate-answer`)

Calculates deterministic keyword coverage and provides feedback.

```bash
curl -X POST "http://localhost:8001/prep/evaluate-answer" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Walk me through your approach to hard-negative mining in the DronaMaps pipeline.",
    "student_answer": "I used sliding window tiling and filtered false positives based on confidence thresholds.",
    "question_tags": [
      "hard negative mining",
      "sliding window tiling",
      "confidence thresholding"
    ]
  }'
```

**Expected Response (HTTP 200):**
```json
{
  "keyword_coverage": 0.67,
  "feedback_text": "Good coverage of sliding window tiling, confidence thresholding — you didn't explicitly name 'hard negative mining' itself, worth stating the term directly.",
  "flagged_as_weak": false
}
```
