from fastapi import APIRouter, Request
from schemas import HealthResponse

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse)
async def get_health(request: Request) -> HealthResponse:
    """
    Health check endpoint.
    'model_loaded' is false until the embedding model has finished loading at startup.
    The backend should treat false as 'not ready yet', not as an error.
    """
    is_loaded = bool(
        getattr(request.app.state, "model_loaded", False)
        and getattr(request.app.state, "model", None) is not None
    )
    return HealthResponse(status="ok", model_loaded=is_loaded)
