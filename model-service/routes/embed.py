from typing import List
from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse

from schemas import EmbedRequest, EmbedResponse, ErrorResponse

router = APIRouter(tags=["Embed"])

MODEL_NAME = "all-MiniLM-L6-v2"
DIMENSION = 384


@router.post(
    "/embed",
    response_model=EmbedResponse,
    responses={
        status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse},
        status.HTTP_503_SERVICE_UNAVAILABLE: {"model": ErrorResponse},
    },
)
async def create_embeddings(payload: EmbedRequest, request: Request):
    """
    Generate real sentence-transformers embeddings for a list of texts (1-50 items).
    Used by the Scout Agent to match resume bullets against JDs via cosine similarity.
    """
    texts = payload.texts

    # Validation: at least 1 text required
    if len(texts) < 1:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": "empty_texts", "detail": "at least 1 text required, got 0"},
        )

    # Validation: max 50 texts per request
    if len(texts) > 50:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error": "too_many_texts",
                "detail": f"max 50 texts per request, got {len(texts)}",
            },
        )

    # Validation: no empty strings
    for idx, text in enumerate(texts):
        if not text or not text.strip():
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"error": "empty_string", "detail": f"texts[{idx}] is empty"},
            )

    # Retrieve model loaded at startup in app.state
    model = getattr(request.app.state, "model", None)
    if model is None:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "error": "model_not_ready",
                "detail": "Embedding model is still loading or unavailable",
            },
        )

    # Generate embeddings using sentence-transformers model
    raw_embeddings = model.encode(texts, convert_to_numpy=True)
    embeddings: List[List[float]] = [
        [round(float(val), 6) for val in emb] for emb in raw_embeddings
    ]

    return EmbedResponse(
        embeddings=embeddings,
        model_name=MODEL_NAME,
        dimension=DIMENSION,
    )
