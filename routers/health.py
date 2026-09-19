import os
import httpx
import logging
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text

from database import get_db
from schemas import HealthStatusResponse

logger = logging.getLogger("placement_copilot.health")
router = APIRouter(tags=["Health"])

MODEL_SERVICE_URL = os.getenv("MODEL_SERVICE_URL", "http://localhost:8001")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")


@router.get("/health", response_model=HealthStatusResponse)
async def check_health(db: Session = Depends(get_db)):
    """
    Comprehensive health check reporting status of:
    - Postgres database connection
    - model-service (:8001)
    - Ollama (:11434)
    - Gmail API authentication token
    """
    services_status = {}

    # 1. Postgres DB Check
    try:
        db.execute(text("SELECT 1"))
        services_status["postgres"] = "healthy"
    except Exception as exc:
        logger.error(f"Postgres health check failed: {exc}")
        services_status["postgres"] = "unhealthy"

    # 2. model-service Check
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get(f"{MODEL_SERVICE_URL}/health")
            if resp.status_code == 200:
                services_status["model_service"] = "healthy"
            else:
                services_status["model_service"] = "unhealthy"
    except Exception:
        services_status["model_service"] = "unhealthy"

    # 3. Ollama Check
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
            if resp.status_code == 200:
                services_status["ollama"] = "healthy"
            else:
                services_status["ollama"] = "unhealthy"
    except Exception:
        services_status["ollama"] = "unhealthy"

    # 4. Gmail API Check
    token_path = os.path.join(os.getcwd(), "token.json")
    if os.path.exists(token_path) or os.getenv("GMAIL_REFRESH_TOKEN"):
        services_status["gmail"] = "healthy"
    else:
        services_status["gmail"] = "unconfigured"

    all_healthy = all(
        v in ("healthy", "unconfigured") for v in services_status.values()
    )
    overall_status = "ok" if all_healthy else "degraded"

    return HealthStatusResponse(status=overall_status, services=services_status)
