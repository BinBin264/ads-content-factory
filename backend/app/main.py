from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import ALLOWED_ORIGINS, UPLOADS_DIR, ensure_app_dirs
from app.models.schemas import HealthResponse
from app.routes.generation import router as generation_router
from app.routes.projects import router as projects_router
from app.services.llm_provider import LLMProviderError
from app.services.storage_service import ProjectNotFoundError


ensure_app_dirs()

app = FastAPI(
    title="AI Ads Video Factory API",
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
    if not detail.startswith("GEMINI_API_KEYS is required"):
        detail = f"Gemini provider failed. Please check GEMINI_API_KEYS and request format. {detail}"
    return JSONResponse(status_code=503, content={"detail": detail})


@app.get("/", response_model=HealthResponse)
def health_check() -> HealthResponse:
    return HealthResponse(status="ok", service="ai-ads-video-factory")


app.include_router(projects_router)
app.include_router(generation_router)
