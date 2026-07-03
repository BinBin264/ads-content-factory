from typing import Annotated

from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import Response

from app.models.schemas import Project
from app.services.project_service import ProjectService


router = APIRouter(prefix="/api/projects", tags=["projects"])
project_service = ProjectService()


@router.post("", response_model=Project, status_code=201)
async def create_project(
    product_name: Annotated[str, Form(...)],
    product_category: Annotated[str | None, Form()] = None,
    product_description: Annotated[str | None, Form()] = None,
    audience: Annotated[str | None, Form()] = None,
    goal: Annotated[str, Form()] = "app_install",
    platform: Annotated[str, Form()] = "tiktok",
    duration: Annotated[str, Form()] = "20s",
    tone: Annotated[str, Form()] = "UGC, natural, realistic",
    cta: Annotated[str | None, Form()] = None,
    claims_to_avoid: Annotated[list[str] | None, Form()] = None,
    brand_colors: Annotated[list[str] | None, Form()] = None,
    files: Annotated[list[UploadFile] | None, File()] = None,
) -> Project:
    return await project_service.create_project(
        product_name=product_name,
        product_category=product_category,
        product_description=product_description,
        audience=audience,
        goal=goal,
        platform=platform,
        duration=duration,
        tone=tone,
        cta=cta,
        claims_to_avoid=claims_to_avoid,
        brand_colors=brand_colors,
        files=files,
    )


@router.get("", response_model=list[Project])
def list_projects() -> list[Project]:
    return project_service.list_projects()


@router.get("/{project_id}", response_model=Project)
def get_project(project_id: str) -> Project:
    return project_service.get_project(project_id)


@router.delete("/{project_id}", status_code=204)
def delete_project(project_id: str) -> Response:
    project_service.delete_project(project_id)
    return Response(status_code=204)
