from fastapi import UploadFile

from app.models.schemas import CreativePlan, Project
from app.services.creative_plan_generator import CreativePlanGenerator, GeminiCreativePlanGenerator
from app.services.storage_service import JsonProjectStorage, LocalFileStorage


class ProjectService:
    def __init__(
        self,
        storage: JsonProjectStorage | None = None,
        file_storage: LocalFileStorage | None = None,
        creative_plan_generator: CreativePlanGenerator | None = None,
    ) -> None:
        self.storage = storage or JsonProjectStorage()
        self.file_storage = file_storage or LocalFileStorage()
        self.creative_plan_generator = creative_plan_generator or GeminiCreativePlanGenerator()

    async def create_project(
        self,
        *,
        product_name: str,
        product_category: str | None,
        product_description: str | None,
        brief: str | None,
        audience: str | None,
        goal: str,
        platform: str,
        duration: str,
        tone: str,
        cta: str | None,
        claims_to_avoid: list[str] | str | None,
        brand_colors: list[str] | str | None,
        files: list[UploadFile] | None,
    ) -> Project:
        project = Project(
            product_name=product_name.strip(),
            product_category=self._clean_optional(product_category),
            product_description=self._clean_optional(product_description),
            brief=self._clean_optional(brief),
            audience=self._clean_optional(audience),
            goal=goal or "app_install",
            platform=platform or "tiktok",
            duration=duration or "20s",
            tone=tone or "UGC, natural, realistic",
            cta=self._clean_optional(cta),
            claims_to_avoid=self._clean_list(claims_to_avoid),
            brand_colors=self._clean_list(brand_colors),
        )
        project.uploaded_files = await self.file_storage.save_uploads(project.id, files)
        return self.storage.save_project(project)

    async def upload_project_files(self, project_id: str, files: list[UploadFile] | None) -> Project:
        if not files:
            raise ValueError("Select at least one file to upload.")
        project = self.storage.get_project(project_id)
        project.uploaded_files.extend(await self.file_storage.save_uploads(project.id, files))
        return self.storage.save_project(project)

    def list_projects(self) -> list[Project]:
        return sorted(self.storage.list_projects(), key=lambda item: item.created_at, reverse=True)

    def get_project(self, project_id: str) -> Project:
        return self.storage.get_project(project_id)

    def generate_plan_creation(self, project_id: str) -> CreativePlan:
        project = self.storage.get_project(project_id)
        result = self.creative_plan_generator.create(project)
        if result.creative_plan is None:
            raise ValueError("Plan Creation generation did not return a creative_plan.")
        project.vision_analysis = result.vision_analysis
        project.creative_plan = result.creative_plan
        self.storage.save_project(project)
        return result.creative_plan

    def delete_project(self, project_id: str) -> None:
        self.storage.delete_project(project_id)

    def _clean_optional(self, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None

    def _clean_list(self, value: list[str] | str | None) -> list[str]:
        if value is None:
            return []

        values = value if isinstance(value, list) else [value]
        cleaned: list[str] = []
        for item in values:
            parts = item.replace("\n", ",").replace(";", ",").split(",")
            cleaned.extend(part.strip() for part in parts if part.strip())
        return cleaned
