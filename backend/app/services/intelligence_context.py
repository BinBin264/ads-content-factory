from typing import Any

from app.models.schemas import Project


def compact_project_context(project: Project) -> dict[str, Any]:
    return {
        "product_name": project.product_name,
        "product_category": project.product_category,
        "product_description": project.product_description,
        "brief": project.brief,
        "audience": project.audience,
        "goal": project.goal,
        "platform": project.platform,
        "duration": project.duration,
        "tone": project.tone,
        "cta": project.cta,
        "claims_to_avoid": project.claims_to_avoid,
        "brand_colors": project.brand_colors,
        "uploaded_files": [file.file_name for file in project.uploaded_files],
    }
