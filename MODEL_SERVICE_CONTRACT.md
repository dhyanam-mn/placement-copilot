# MODEL_SERVICE_CONTRACT.md

**Owner:** Dhyanam | **Runs on:** `http://localhost:8001` | **Consumed by:** Aadya's FastAPI backend, exactly like a third-party API (same pattern as SerpAPI)

This service is the only GPU-dependent piece of the system. It exposes four endpoints. Everything below is the source of truth both sides build against — if either side needs to change a shape, update this file first and re-sync before touching code.

---

## GET /health

**Response**
```json
{
  "status": "ok",
  "model_loaded": true
}
```
`model_loaded` is `false` until the embedding model has finished loading at startup — the backend should treat `false` as "not ready yet," not as an error.

---

## POST /embed

Used by the **Scout Agent** to match resume bullets against job descriptions via cosine similarity.

**Request**
```json
{
  "texts": [
    "Built a drone orthomosaic detection pipeline using GeoTIFF and rasterio.",
    "Looking for an intern experienced in object detection and satellite imagery."
  ]
}
```
- `texts`: list of strings, 1–50 items, no empty strings.

**Response**
```json
{
  "embeddings": [
    [0.0123, -0.0456, 0.0789, "... 384 floats total"],
    [0.0201, -0.0333, 0.0650, "... 384 floats total"]
  ],
  "model_name": "all-MiniLM-L6-v2",
  "dimension": 384
}
```
- `embeddings[i]` corresponds to `texts[i]`, same order, same length.

**Errors**
```json
{ "error": "empty_string", "detail": "texts[1] is empty" }
```
```json
{ "error": "too_many_texts", "detail": "max 50 texts per request, got 63" }
```

---

## POST /llm-generate

Used for the **three, and only three**, LLM calls in the whole system. `task_type` determines the shape of `context`.

**Request — task_type: "scam_explanation"**
```json
{
  "task_type": "scam_explanation",
  "context": {
    "flagged_reasons": [
      "sender domain does not match company's official domain",
      "requests processing fee before interview"
    ],
    "recruiter_info": {
      "name": "Rohan Sharma",
      "claimed_company": "TechNova Solutions",
      "email_domain": "technova-careers.in"
    }
  }
}
```
Note: the flag/no-flag decision is already made by the rule layer before this is called. This endpoint only phrases *why*, it never decides.

**Request — task_type: "answer_feedback"**
```json
{
  "task_type": "answer_feedback",
  "context": {
    "question": "Walk me through your approach to hard-negative mining in the DronaMaps pipeline.",
    "student_answer": "I used sliding window tiling and filtered false positives based on confidence thresholds.",
    "expected_topics": ["hard negative mining", "sliding window tiling", "confidence thresholding"]
  }
}
```

**Request — task_type: "gap_summary"**
```json
{
  "task_type": "gap_summary",
  "context": {
    "rejected_applications": [
      { "role_tag": "SDE", "rejection_stage": "OA" },
      { "role_tag": "SDE", "rejection_stage": "OA" },
      { "role_tag": "SDE", "rejection_stage": "INTERVIEW" },
      { "role_tag": "CV", "rejection_stage": "INTERVIEW" }
    ]
  }
}
```
Note: the underlying counts/stats are computed deterministically by the backend before this call — this endpoint only turns already-computed stats into a plain-English sentence, it does not calculate the pattern itself.

**Response (same shape for all three task_types)**
```json
{
  "generated_text": "This looks risky: the sender's email domain doesn't match TechNova's official domain, and asking for a processing fee before any interview is a common red flag.",
  "task_type": "scam_explanation"
}
```

**Errors / fallback**
If Ollama is unreachable or times out (10s), respond with:
```json
{
  "generated_text": "",
  "task_type": "scam_explanation",
  "error": "llm_unavailable"
}
```
The backend must handle `error: "llm_unavailable"` gracefully (e.g. show the deterministic `flagged_reasons` list without a phrased explanation) — a demo should never hard-fail because Ollama hiccuped.

---

## POST /prep/evaluate-answer

Used by the **Prep Agent's** feedback loop. Combines a cheap deterministic check with the LLM call above internally.

**Request**
```json
{
  "question": "Walk me through your approach to hard-negative mining in the DronaMaps pipeline.",
  "student_answer": "I used sliding window tiling and filtered false positives based on confidence thresholds.",
  "question_tags": ["hard negative mining", "sliding window tiling", "confidence thresholding"]
}
```

**Response**
```json
{
  "keyword_coverage": 0.67,
  "feedback_text": "Good coverage of tiling and thresholding — you didn't explicitly name 'hard negative mining' itself, worth stating the term directly.",
  "flagged_as_weak": false
}
```
- `keyword_coverage`: fraction of `question_tags` found (case-insensitive substring match) in `student_answer`, computed **before** any LLM call — instant, no model dependency.
- `flagged_as_weak`: `true` if `keyword_coverage < 0.3`.
- `feedback_text`: from the internal `/llm-generate` call with `task_type: "answer_feedback"`. If that call fails, fall back to `"Keyword coverage: {keyword_coverage}. LLM feedback unavailable."`

---

## Testing without a real model

Until Prompt 3/4 (real embeddings/Ollama) are done, `/embed` and `/llm-generate` may return dummy data **matching these exact shapes**, so Aadya can build against them immediately without waiting.
