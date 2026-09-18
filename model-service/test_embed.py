"""
Sanity-check script for /embed endpoint.
Sends sample resume bullets and Job Description (JD) strings,
computes cosine similarity between their embeddings, and prints the similarity scores.

Can be run:
1. Against a live server running at http://localhost:8001 (e.g. `uvicorn main:app --port 8001`)
2. Standalone directly: `python test_embed.py` (falls back to TestClient)
"""

import sys
import math
from typing import List
import requests

SERVER_URL = "http://localhost:8001/embed"


def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """Compute cosine similarity between two float vectors."""
    dot_product = sum(a * b for a, b in zip(v1, v2))
    norm_v1 = math.sqrt(sum(a * a for a in v1))
    norm_v2 = math.sqrt(sum(b * b for b in v2))
    if norm_v1 == 0 or norm_v2 == 0:
        return 0.0
    return dot_product / (norm_v1 * norm_v2)


def get_embeddings(texts: List[str]) -> List[List[float]]:
    """Retrieve embeddings via live server HTTP or fallback to TestClient."""
    try:
        resp = requests.post(SERVER_URL, json={"texts": texts}, timeout=5)
        if resp.status_code == 200:
            return resp.json()["embeddings"]
    except Exception:
        pass

    # Fallback to direct FastAPI TestClient with lifespan
    print("[Info] Live server not detected at http://localhost:8001. Running with in-memory TestClient...")
    from fastapi.testclient import TestClient
    from main import app

    with TestClient(app) as client:
        resp = client.post("/embed", json={"texts": texts})
        if resp.status_code != 200:
            raise RuntimeError(f"Failed to get embeddings: {resp.status_code} {resp.text}")
        return resp.json()["embeddings"]


def main():
    print("=" * 80)
    print("Placement-Copilot: Scout Agent Cosine Similarity Sanity Check")
    print("=" * 80)

    # Test cases: (Resume Bullet, JD String, Expected Relation)
    test_cases = [
        {
            "category": "Computer Vision / Remote Sensing",
            "bullet": "Built a drone orthomosaic detection pipeline using GeoTIFF and rasterio.",
            "jd_similar": "Looking for an intern experienced in object detection, GeoTIFF processing, and satellite imagery.",
            "jd_dissimilar": "Hiring a financial auditor and tax consultant experienced in GST reconciliation and filing.",
        },
        {
            "category": "Backend Systems & Databases",
            "bullet": "Designed and scaled backend microservices using FastAPI, PostgreSQL, and Redis caching.",
            "jd_similar": "Seeking a backend engineer proficient in Python web frameworks, SQL databases, and distributed caching.",
            "jd_dissimilar": "Looking for a fashion stylist and visual merchandiser for an e-commerce retail store.",
        },
    ]

    all_passed = True

    for idx, case in enumerate(test_cases, 1):
        print(f"\n--- Test Group {idx}: {case['category']} ---")
        bullet = case["bullet"]
        jd_sim = case["jd_similar"]
        jd_diff = case["jd_dissimilar"]

        print(f"Resume Bullet:\n  \"{bullet}\"\n")

        # Get embeddings for bullet, similar JD, and dissimilar JD in one batch
        embeddings = get_embeddings([bullet, jd_sim, jd_diff])
        emb_bullet, emb_sim, emb_diff = embeddings[0], embeddings[1], embeddings[2]

        score_sim = cosine_similarity(emb_bullet, emb_sim)
        score_diff = cosine_similarity(emb_bullet, emb_diff)

        print(f"1. Related JD:\n   \"{jd_sim}\"")
        print(f"   Cosine Similarity: {score_sim:.4f}")
        is_sim_ok = score_sim >= 0.50
        print(f"   Match Evaluation:  {'PASS (High match)' if is_sim_ok else 'FAIL (Expected >= 0.50)'}\n")

        print(f"2. Unrelated JD:\n   \"{jd_diff}\"")
        print(f"   Cosine Similarity: {score_diff:.4f}")
        is_diff_ok = score_diff < 0.30
        print(f"   Match Evaluation:  {'PASS (Low match)' if is_diff_ok else 'FAIL (Expected < 0.30)'}\n")

        # Sanity check: similar match must score significantly higher than unrelated
        delta = score_sim - score_diff
        print(f"   Separation Margin: {delta:.4f} (Similar vs Dissimilar)")
        if not (is_sim_ok and is_diff_ok and delta > 0.30):
            all_passed = False

    print("=" * 80)
    if all_passed:
        print("[SUCCESS] All sanity checks passed! Similar bullets receive high cosine similarity scores.")
    else:
        print("[WARNING] One or more tests did not meet the expected similarity thresholds.")
    print("=" * 80)


if __name__ == "__main__":
    main()
