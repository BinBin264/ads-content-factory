from fastapi import APIRouter

from app.models.schemas import CreativePlan
from app.routes.projects import project_service


router = APIRouter(prefix="/api/projects", tags=["generation"])


@router.post("/{project_id}/plan-creation", response_model=CreativePlan)
def generate_plan_creation(project_id: str) -> CreativePlan:
    return project_service.generate_plan_creation(project_id)
