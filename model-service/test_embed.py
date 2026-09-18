"""
Placement Copilot: Scout Agent Cosine Similarity Sanity Check

Sends sample resume bullets and Job Description (JD) strings to /embed,
computes cosine similarity between their embedding vectors, and verifies that
semantically related JDs score significantly higher than unrelated JDs.

Usage:
1. Against a live server running at http://localhost:8001:
   python test_embed.py
2. Direct in-memory test using FastAPI TestClient (automatic fallback if server is offline):
   python test_embed.py
"""

import sys
import math
from typing import List, Tuple
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


class EmbedClient:
    """Helper client that connects to live server or falls back to in-memory TestClient."""

    def __init__(self):
        self.use_live = False
        self._test_client = None

        # Check if live server is reachable
        try:
            resp = requests.get("http://localhost:8001/health", timeout=2)
            if resp.status_code == 200:
                self.use_live = True
                print("[Info] Connected to live model-service at http://localhost:8001")
        except Exception:
            self.use_live = False

        if not self.use_live:
            print("[Info] Live server not detected at http://localhost:8001. Running with in-memory TestClient...")
            from fastapi.testclient import TestClient
            from main import app

            self._cm = TestClient(app)
            self._test_client = self._cm.__enter__()

    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        if self.use_live:
            resp = requests.post(SERVER_URL, json={"texts": texts}, timeout=10)
            if resp.status_code != 200:
                raise RuntimeError(f"HTTP {resp.status_code} Error: {resp.text}")
            return resp.json()["embeddings"]
        else:
            resp = self._test_client.post("/embed", json={"texts": texts})
            if resp.status_code != 200:
                raise RuntimeError(f"TestClient Error {resp.status_code}: {resp.text}")
            return resp.json()["embeddings"]

    def close(self):
        if not self.use_live and self._cm:
            self._cm.__exit__(None, None, None)


def main():
    print("=" * 80)
    print("Placement-Copilot: Scout Agent Cosine Similarity Sanity Check")
    print("=" * 80)

    client = EmbedClient()

    try:
        # Test cases: (Category, Resume Bullet, Relevant JD, Unrelated JD)
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
            {
                "category": "Machine Learning / NLP",
                "bullet": "Fine-tuned Llama 3 models using LoRA and PyTorch for domain-specific text classification.",
                "jd_similar": "Seeking an ML engineer with PyTorch expertise in fine-tuning large language models and transformers.",
                "jd_dissimilar": "Recruiting a site civil engineer for construction site inspection and structural design.",
            },
        ]

        all_passed = True

        for idx, case in enumerate(test_cases, 1):
            print(f"\n--- Test Group {idx}: {case['category']} ---")
            bullet = case["bullet"]
            jd_sim = case["jd_similar"]
            jd_diff = case["jd_dissimilar"]

            print(f"Resume Bullet:\n  \"{bullet}\"\n")

            # Request embeddings for bullet, similar JD, and dissimilar JD in a single batch
            embeddings = client.get_embeddings([bullet, jd_sim, jd_diff])
            emb_bullet, emb_sim, emb_diff = embeddings[0], embeddings[1], embeddings[2]

            score_sim = cosine_similarity(emb_bullet, emb_sim)
            score_diff = cosine_similarity(emb_bullet, emb_diff)

            print(f"1. Related Job Description:\n   \"{jd_sim}\"")
            print(f"   Cosine Similarity Score: {score_sim:.4f}")

            print(f"2. Unrelated Job Description:\n   \"{jd_diff}\"")
            print(f"   Cosine Similarity Score: {score_diff:.4f}")

            # Calculate margin between related and unrelated match
            margin = score_sim - score_diff
            print(f"\n   Separation Margin:       {margin:+.4f} (Related vs Unrelated)")

            # Evaluation criteria:
            # 1. Related score must be significantly higher than unrelated score (margin >= 0.20)
            # 2. Related score must be positive (> 0.25)
            is_valid = (score_sim > 0.25) and (score_diff < 0.20) and (margin >= 0.20)

            if is_valid:
                print("   Result:                  PASS (Strong semantic differentiation)")
            else:
                print("   Result:                  FAIL (Expected higher separation margin)")
                all_passed = False

        print("\n" + "=" * 80)
        if all_passed:
            print("[SUCCESS] All sanity checks passed! Similar text gets high cosine similarity scores.")
        else:
            print("[WARNING] One or more tests did not meet the expected similarity thresholds.")
        print("=" * 80)

    finally:
        client.close()


if __name__ == "__main__":
    main()
