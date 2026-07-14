from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import ALLOWED_ORIGINS, UPLOADS_DIR, ensure_app_dirs
from app.models.schemas import HealthResponse
from app.routes.generation import router as generation_router
from app.routes.projects import router as projects_router
from app.services.image_provider import ImageProviderError
from app.services.llm_provider import LLMProviderError
from app.services.storage_service import ProjectNotFoundError
from app.services.video_provider import VideoProviderError


ensure_app_dirs()

app = FastAPI(
    title="AI Video Factory API",
    version="0.1.0",
    description="Backend MVP for turning a brief and uploaded assets into a Plan Creation workflow.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")


@app.exception_handler(ProjectNotFoundError)
async def project_not_found_handler(_: Request, exc: ProjectNotFoundError) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(ValueError)
async def value_error_handler(_: Request, exc: ValueError) -> JSONResponse:
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.exception_handler(LLMProviderError)
async def llm_provider_error_handler(_: Request, exc: LLMProviderError) -> JSONResponse:
    detail = str(exc)
    if detail.startswith("GEMINI_API_KEYS is required"):
        pass
    elif "Gemini API HTTP 503" in detail or '"status": "UNAVAILABLE"' in detail:
        detail = f"Gemini model is temporarily unavailable or experiencing high demand. Retry later. {detail}"
    elif "Gemini API HTTP 429" in detail:
        detail = f"Gemini quota or rate limit was reached. Check the active key quota and retry later. {detail}"
    elif "Gemini API request timed out" in detail:
        detail = f"Gemini did not respond before the configured timeout after retrying. Retry the action later or increase GEMINI_REQUEST_TIMEOUT_SECONDS. {detail}"
    elif "Gemini API request failed" in detail:
        detail = f"Gemini could not be reached after retrying. Check the network connection and retry. {detail}"
    elif "API_KEY_INVALID" in detail:
        detail = f"A configured Gemini API key is invalid. Remove or replace the invalid key. {detail}"
    else:
        detail = f"Gemini provider failed. Please check GEMINI_API_KEYS and request format. {detail}"
    return JSONResponse(status_code=503, content={"detail": detail})


@app.exception_handler(ImageProviderError)
async def image_provider_error_handler(_: Request, exc: ImageProviderError) -> JSONResponse:
    return JSONResponse(status_code=503, content={"detail": str(exc)})


@app.exception_handler(VideoProviderError)
async def video_provider_error_handler(_: Request, exc: VideoProviderError) -> JSONResponse:
    return JSONResponse(status_code=503, content={"detail": str(exc)})


@app.get("/", response_model=HealthResponse)
def health_check() -> HealthResponse:
    return HealthResponse(status="ok", service="ai-video-factory")


app.include_router(projects_router)
app.include_router(generation_router)
