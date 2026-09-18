import hashlib
from typing import List
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from schemas import EmbedRequest, EmbedResponse, ErrorResponse

router = APIRouter(tags=["Embed"])

MODEL_NAME = "all-MiniLM-L6-v2"
DIMENSION = 384


def generate_dummy_embedding(text: str, dim: int = DIMENSION) -> List[float]:
    """
    Generate deterministic placeholder embedding vector of specified dimension
    based on the hash of the input text.
    """
    seed = int(hashlib.sha256(text.encode("utf-8")).hexdigest()[:8], 16)
    vector: List[float] = []
    current = seed
    for _ in range(dim):
        current = (current * 1103515245 + 12345) & 0x7FFFFFFF
        val = ((current / 0x7FFFFFFF) * 2.0 - 1.0) * 0.1
        vector.append(round(val, 4))
    return vector


@router.post(
    "/embed",
    response_model=EmbedResponse,
    responses={
        status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse},
    },
)
async def create_embeddings(payload: EmbedRequest):
    """
    Generate embeddings for a list of texts (1-50 items).
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

    # Generate placeholder embeddings
    embeddings = [generate_dummy_embedding(text) for text in texts]

    return EmbedResponse(
        embeddings=embeddings,
        model_name=MODEL_NAME,
        dimension=DIMENSION,
    )
