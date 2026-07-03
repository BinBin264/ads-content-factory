from fastapi import APIRouter

from app.models.schemas import AnalyzeProjectResponse, CreativeAngle, GenerateVariantsRequest, Project, Variant
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


@router.post("/{project_id}/render", response_model=Project)
def render(project_id: str) -> Project:
    return project_service.render_videos(project_id)
