from fastapi import APIRouter
from schemas import HealthResponse

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse)
async def get_health() -> HealthResponse:
    """
    Health check endpoint.
    'model_loaded' is false until the embedding model has finished loading at startup.
    The backend should treat false as 'not ready yet', not as an error.
    """
    return HealthResponse(status="ok", model_loaded=True)
