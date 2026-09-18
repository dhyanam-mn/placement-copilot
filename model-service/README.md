# Model Service

FastAPI microservice implementing the specifications defined in [`MODEL_SERVICE_CONTRACT.md`](../MODEL_SERVICE_CONTRACT.md).

This service runs on port `8001` and provides embedding generation (`all-MiniLM-L6-v2`) and LLM text generation endpoints (powered by local **Ollama** `llama3.1:8b`).

---

## Getting Started

### 1. Install Dependencies

From the `model-service` directory:

```bash
pip install -r requirements.txt
```

### 2. Setting Up Local Ollama (`llama3.1:8b`)

The `/llm-generate` endpoint calls a local Ollama instance running at `http://localhost:11434/api/generate` to generate text for scam explanations, interview answer feedback, and application gap summaries.

#### Step A: Install Ollama
- **Windows**: Download from [ollama.com/download/windows](https://ollama.com/download/windows) or run:
  ```powershell
  winget install Ollama.Ollama
  ```
- **macOS**:
  ```bash
  brew install ollama
  ```
- **Linux**:
  ```bash
  curl -fsSL https://ollama.com/install.sh | sh
  ```

#### Step B: Pull `llama3.1:8b` Model
Run the following command in your terminal:

```bash
ollama pull llama3.1:8b
```

#### Step C: Verify Ollama Service
Start the Ollama daemon (if not already running):

```bash
ollama serve
```

Verify that Ollama is active by checking the local tags API:

```bash
curl http://localhost:11434/api/tags
```

> **Automatic Fallback Mode:**
> If Ollama is unreachable or times out (>10s limit), `model-service` gracefully returns a deterministic fallback response (`error: "llm_unavailable"`) so the rest of Placement Copilot's pipeline never breaks.

---

### 3. Run the Model Service

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

## Endpoint Specifications

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

Generates 384-dimensional sentence embeddings using `all-MiniLM-L6-v2` loaded at app startup.

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
    [-0.0245, 0.0812, "... 384 floats total"],
    [-0.0189, 0.0765, "... 384 floats total"]
  ],
  "model_name": "all-MiniLM-L6-v2",
  "dimension": 384
}
```

---

### 3. LLM Generation (`POST /llm-generate`)

Calls local Ollama (`llama3.1:8b`) with task-specific prompts for judgment and feedback generation.

#### A. Task: `scam_explanation`

Explains why an outreach email was flagged by the Scam-Check Agent rule layer.

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

#### B. Task: `answer_feedback`

Evaluates student mock interview responses and provides targeted feedback.

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

#### C. Task: `gap_summary`

Identifies bottlenecks and common patterns across rejected/ghosted applications.

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

---

## Testing

Run all unit and smoke tests:

```bash
python test_service.py
```

Run embedding cosine similarity sanity checks:

```bash
python test_embed.py
```
