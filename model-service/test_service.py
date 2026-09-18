import json
import pytest
from fastapi.testclient import TestClient
from main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["model_loaded"] is True
    print("[OK] /health passed")


def test_embed_success(client):
    payload = {
        "texts": [
            "Built a drone orthomosaic detection pipeline using GeoTIFF and rasterio.",
            "Looking for an intern experienced in object detection and satellite imagery."
        ]
    }
    response = client.post("/embed", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["model_name"] == "all-MiniLM-L6-v2"
    assert data["dimension"] == 384
    assert len(data["embeddings"]) == 2
    assert len(data["embeddings"][0]) == 384
    assert len(data["embeddings"][1]) == 384
    print("[OK] /embed success passed")


def test_embed_empty_string_error(client):
    payload = {
        "texts": [
            "Valid bullet point",
            ""
        ]
    }
    response = client.post("/embed", json=payload)
    assert response.status_code == 400
    data = response.json()
    assert data["error"] == "empty_string"
    assert data["detail"] == "texts[1] is empty"
    print("[OK] /embed empty string error passed")


def test_embed_too_many_texts_error(client):
    payload = {
        "texts": ["item" for _ in range(55)]
    }
    response = client.post("/embed", json=payload)
    assert response.status_code == 400
    data = response.json()
    assert data["error"] == "too_many_texts"
    assert "max 50 texts per request, got 55" in data["detail"]
    print("[OK] /embed too many texts error passed")


def test_llm_generate_scam_explanation(client):
    payload = {
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
    response = client.post("/llm-generate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["task_type"] == "scam_explanation"
    assert len(data["generated_text"]) > 0 or data.get("error") == "llm_unavailable"
    print("[OK] /llm-generate scam_explanation passed")


def test_llm_generate_answer_feedback(client):
    payload = {
        "task_type": "answer_feedback",
        "context": {
            "question": "Walk me through your approach to hard-negative mining in the DronaMaps pipeline.",
            "student_answer": "I used sliding window tiling and filtered false positives based on confidence thresholds.",
            "expected_topics": ["hard negative mining", "sliding window tiling", "confidence thresholding"]
        }
    }
    response = client.post("/llm-generate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["task_type"] == "answer_feedback"
    assert len(data["generated_text"]) > 0 or data.get("error") == "llm_unavailable"
    print("[OK] /llm-generate answer_feedback passed")


def test_llm_generate_gap_summary(client):
    payload = {
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
    response = client.post("/llm-generate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["task_type"] == "gap_summary"
    assert len(data["generated_text"]) > 0 or data.get("error") == "llm_unavailable"
    print("[OK] /llm-generate gap_summary passed")


def test_prep_evaluate_answer(client):
    payload = {
        "question": "Walk me through your approach to hard-negative mining in the DronaMaps pipeline.",
        "student_answer": "I used sliding window tiling and filtered false positives based on confidence thresholds.",
        "question_tags": ["hard negative mining", "sliding window tiling", "confidence thresholding"]
    }
    response = client.post("/prep/evaluate-answer", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["keyword_coverage"] == 0.67
    assert data["flagged_as_weak"] is False
    assert len(data["feedback_text"]) > 0
    print("[OK] /prep/evaluate-answer passed")


if __name__ == "__main__":
    with TestClient(app) as test_c:
        test_health(test_c)
        test_embed_success(test_c)
        test_embed_empty_string_error(test_c)
        test_embed_too_many_texts_error(test_c)
        test_llm_generate_scam_explanation(test_c)
        test_llm_generate_answer_feedback(test_c)
        test_llm_generate_gap_summary(test_c)
        test_prep_evaluate_answer(test_c)
        print("\nAll 8 smoke tests passed successfully!")
