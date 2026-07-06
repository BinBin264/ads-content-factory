from fastapi import APIRouter, File, Form, UploadFile

from app.models.schemas import AnalyzeProjectResponse, CreativeAngle, GenerateVariantsRequest, Project, Variant, VariantGenerationPipeline
from app.routes.projects import project_service


router = APIRouter(prefix="/api/projects", tags=["generation"])


@router.post("/{project_id}/analyze", response_model=AnalyzeProjectResponse)
def analyze_project(project_id: str) -> AnalyzeProjectResponse:
    return project_service.analyze_project(project_id)


@router.post("/{project_id}/angles", response_model=list[CreativeAngle])
def generate_angles(project_id: str) -> list[CreativeAngle]:
    return project_service.generate_angles(project_id)


@router.post("/{project_id}/generate-variants", response_model=list[Variant])
def generate_variants(project_id: str, request: GenerateVariantsRequest) -> list[Variant]:
    return project_service.generate_variants(project_id, request)


@router.post("/{project_id}/export-production-package", response_model=Project)
def export_production_package(project_id: str) -> Project:
    return project_service.export_production_package(project_id)


@router.get("/{project_id}/variants/{variant_id}/pipeline", response_model=VariantGenerationPipeline)
def get_generation_pipeline(project_id: str, variant_id: str) -> VariantGenerationPipeline:
    return project_service.get_generation_pipeline(project_id, variant_id)


@router.post("/{project_id}/variants/{variant_id}/pipeline/steps/{step_id}/upload-result", response_model=Project)
async def upload_pipeline_step_result(
    project_id: str,
    variant_id: str,
    step_id: str,
    file: UploadFile = File(...),
    asset_key: str | None = Form(default=None),
    notes: str | None = Form(default=None),
) -> Project:
    return await project_service.upload_pipeline_step_result(project_id, variant_id, step_id, file, asset_key, notes)


@router.post("/{project_id}/variants/{variant_id}/pipeline/steps/{step_id}/run", response_model=Project)
def run_pipeline_step(project_id: str, variant_id: str, step_id: str) -> Project:
    return project_service.run_pipeline_step(project_id, variant_id, step_id)


@router.post("/{project_id}/variants/{variant_id}/pipeline/run", response_model=Project)
def run_variant_pipeline(project_id: str, variant_id: str) -> Project:
    return project_service.run_variant_pipeline(project_id, variant_id)


@router.post("/{project_id}/render", response_model=Project)
def render(project_id: str) -> Project:
    return project_service.render_videos(project_id)
