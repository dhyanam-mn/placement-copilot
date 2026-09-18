import os
import logging
from typing import Any, Dict, List
import httpx
from fastapi import HTTPException, status

logger = logging.getLogger("uvicorn.info")

MODEL_SERVICE_URL = os.getenv("MODEL_SERVICE_URL", "http://localhost:8001")


class ModelServiceUnavailableError(HTTPException):
    def __init__(self, detail: str):
        super().__init__(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"error": "model_service_unavailable", "detail": detail},
        )


async def call_embed(texts: List[str]) -> Dict[str, Any]:
    """Call model-service POST /embed"""
    url = f"{MODEL_SERVICE_URL}/embed"
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(url, json={"texts": texts})
            if resp.status_code != 200:
                raise ModelServiceUnavailableError(
                    f"model-service /embed returned status {resp.status_code}: {resp.text}"
                )
            return resp.json()
    except httpx.HTTPError as exc:
        logger.error(f"Failed to connect to model-service at {url}: {exc}")
        raise ModelServiceUnavailableError(
            f"Could not connect to model-service at {MODEL_SERVICE_URL}"
        )


async def call_llm_generate(task_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """Call model-service POST /llm-generate"""
    url = f"{MODEL_SERVICE_URL}/llm-generate"
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(url, json={"task_type": task_type, "context": context})
            if resp.status_code != 200:
                raise ModelServiceUnavailableError(
                    f"model-service /llm-generate returned status {resp.status_code}: {resp.text}"
                )
            return resp.json()
    except httpx.HTTPError as exc:
        logger.error(f"Failed to connect to model-service at {url}: {exc}")
        raise ModelServiceUnavailableError(
            f"Could not connect to model-service at {MODEL_SERVICE_URL}"
        )


async def call_prep_evaluate_answer(question: str, student_answer: str, question_tags: List[str]) -> Dict[str, Any]:
    """Call model-service POST /prep/evaluate-answer"""
    url = f"{MODEL_SERVICE_URL}/prep/evaluate-answer"
    payload = {
        "question": question,
        "student_answer": student_answer,
        "question_tags": question_tags,
    }
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code != 200:
                raise ModelServiceUnavailableError(
                    f"model-service /prep/evaluate-answer returned status {resp.status_code}: {resp.text}"
                )
            return resp.json()
    except httpx.HTTPError as exc:
        logger.error(f"Failed to connect to model-service at {url}: {exc}")
        raise ModelServiceUnavailableError(
            f"Could not connect to model-service at {MODEL_SERVICE_URL}"
        )
