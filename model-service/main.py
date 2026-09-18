import os
import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Ensure the model-service directory is on sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from routes.health import router as health_router
from routes.embed import router as embed_router
from routes.generate import router as generate_router
from routes.prep import router as prep_router

app = FastAPI(
    title="Placement Copilot Model Service",
    description="GPU-dependent embedding and LLM generation service implementing MODEL_SERVICE_CONTRACT.md",
    version="0.1.0",
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
app.include_router(prep_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
