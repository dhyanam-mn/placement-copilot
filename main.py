import os
import sys
import logging
from fastapi import FastAPI, Request, HTTPException, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

# Ensure workspace root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from contextlib import asynccontextmanager
from routers.applications import router as applications_router
from routers.notifications import router as notifications_router
from routers.profile import router as profile_router
from routers.resources import router as resources_router
from routers.skills import router as skills_router
from routers.scam_patterns import router as scam_patterns_router
from routers.watchlist import router as watchlist_router
from routers.settings import router as settings_router
from routers.health import router as health_router
from routers.gmail import router as gmail_router
from routers.admin import router as admin_router
from routers.scheduler import router as scheduler_router
from services.scheduler import start_scheduler, shutdown_scheduler

logger = logging.getLogger("uvicorn.info")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager starting APScheduler on startup and shutting down on shutdown."""
    logger.info("Starting Placement Copilot FastAPI application...")
    start_scheduler()
    yield
    shutdown_scheduler()
    logger.info("Placement Copilot FastAPI application shut down.")


app = FastAPI(
    title="Placement Copilot Backend",
    description="FastAPI Backend for Placement Copilot implementing complete API contract, autonomous agents, and administration.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Standardized Error Shape Handlers ---

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Format HTTP exceptions into contract error shape: { 'error': '...', 'detail': '...' }"""
    if isinstance(exc.detail, dict) and "error" in exc.detail:
        return JSONResponse(status_code=exc.status_code, content=exc.detail)

    error_code = "error"
    if exc.status_code == 404:
        error_code = "not_found"
    elif exc.status_code == 422:
        error_code = "validation_error"
    elif exc.status_code == 502:
        error_code = "model_service_unavailable"

    return JSONResponse(
        status_code=exc.status_code,
        content={"error": error_code, "detail": str(exc.detail)},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Format Pydantic validation errors into contract shape: { 'error': 'validation_error', 'detail': '...' }"""
    errors_summary = []
    for err in exc.errors():
        loc_str = " -> ".join([str(l) for l in err.get("loc", [])])
        msg = err.get("msg", "invalid value")
        errors_summary.append(f"{loc_str}: {msg}")

    detail_str = "; ".join(errors_summary) if errors_summary else str(exc)
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"error": "validation_error", "detail": detail_str},
    )


# Register routers
app.include_router(applications_router)
app.include_router(notifications_router)
app.include_router(profile_router)
app.include_router(resources_router)
app.include_router(skills_router)
app.include_router(scam_patterns_router)
app.include_router(watchlist_router)
app.include_router(settings_router)
app.include_router(health_router)
app.include_router(gmail_router)
app.include_router(admin_router)
app.include_router(scheduler_router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
