import os
import sys
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sentence_transformers import SentenceTransformer

# Ensure the model-service directory is on sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from routes.health import router as health_router
from routes.embed import router as embed_router
from routes.generate import router as generate_router

logger = logging.getLogger("uvicorn.info")
MODEL_NAME = "all-MiniLM-L6-v2"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Load the sentence-transformers model once at app startup and store in app.state.
    /health reports model_loaded: true once this finishes.
    """
    app.state.model = None
    app.state.model_loaded = False
    logger.info(f"Loading embedding model '{MODEL_NAME}' at startup...")
    try:
        model = SentenceTransformer(MODEL_NAME)
        app.state.model = model
        app.state.model_loaded = True
        logger.info(f"Successfully loaded '{MODEL_NAME}' into app.state.")
    except Exception as e:
        logger.error(f"Error loading model '{MODEL_NAME}': {e}", exc_info=True)
        app.state.model_loaded = False

    yield

    # Teardown
    app.state.model = None
    app.state.model_loaded = False
    logger.info("Model unloaded on shutdown.")


app = FastAPI(
    title="Placement Copilot Model Service",
    description="GPU-dependent embedding and LLM generation service implementing MODEL_SERVICE_CONTRACT.md",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register route modules
app.include_router(health_router)
app.include_router(embed_router)
app.include_router(generate_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)
