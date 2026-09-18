import os
import sys
import logging
from fastapi import FastAPI, Request, HTTPException, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

# Ensure workspace root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from routers.applications import router as applications_router
from routers.gmail import router as gmail_router

logger = logging.getLogger("uvicorn.info")

app = FastAPI(
    title="Placement Copilot Backend",
    description="FastAPI Backend for Placement Copilot implementing API_CONTRACT.md",
    version="1.0.0",
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
app.include_router(gmail_router)


@app.get("/health")
def backend_health():
    return {"status": "ok", "service": "placement-copilot-backend"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
