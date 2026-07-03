from fastapi import UploadFile

from app.models.schemas import AnalyzeProjectResponse, CreativeAngle, GenerateVariantsRequest, ProductBrief, Project, Variant, VisionAnalysis
from app.services.angle_generator import CreativeAngleGenerator, RuleBasedCreativeAngleGenerator
from app.services.product_analyzer import ProductAnalyzer, RuleBasedProductAnalyzer
from app.services.script_generator import RuleBasedVariantScriptGenerator, VariantScriptGenerator
from app.services.storage_service import JsonProjectStorage, LocalFileStorage
from app.services.video_provider import MockVideoProvider, VideoProvider


class ProjectService:
    def __init__(
        self,
        storage: JsonProjectStorage | None = None,
        file_storage: LocalFileStorage | None = None,
        analyzer: ProductAnalyzer | None = None,
        angle_generator: CreativeAngleGenerator | None = None,
        script_generator: VariantScriptGenerator | None = None,
        video_provider: VideoProvider | None = None,
    ) -> None:
        self.storage = storage or JsonProjectStorage()
        self.file_storage = file_storage or LocalFileStorage()
        self.analyzer = analyzer or RuleBasedProductAnalyzer()
        self.angle_generator = angle_generator or RuleBasedCreativeAngleGenerator()
        self.script_generator = script_generator or RuleBasedVariantScriptGenerator()
        self.video_provider = video_provider or MockVideoProvider()

    async def create_project(
        self,
        *,
        product_name: str,
        product_category: str | None,
        product_description: str | None,
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

    def list_projects(self) -> list[Project]:
        return sorted(self.storage.list_projects(), key=lambda item: item.created_at, reverse=True)

    def get_project(self, project_id: str) -> Project:
        return self.storage.get_project(project_id)

    def analyze_project(self, project_id: str) -> AnalyzeProjectResponse:
        project = self.storage.get_project(project_id)
        analysis = self.analyzer.analyze(project)
        project.vision_analysis = analysis.vision_analysis
        project.product_intelligence = analysis.product_intelligence
        project.product_brief = analysis.product_brief
        self.storage.save_project(project)
        return analysis

    def generate_angles(self, project_id: str) -> list[CreativeAngle]:
        project = self.storage.get_project(project_id)
        analysis = self._ensure_analysis(project)
        brief = analysis.product_brief
        intelligence = analysis.product_intelligence
        project.product_brief = brief
        project.product_intelligence = intelligence
        project.vision_analysis = analysis.vision_analysis
        project.creative_angles = self.angle_generator.generate(project, brief, intelligence)
        self.storage.save_project(project)
        return project.creative_angles

    def generate_variants(self, project_id: str, request: GenerateVariantsRequest) -> list[Variant]:
        project = self.storage.get_project(project_id)
        analysis = self._ensure_analysis(project)
        brief = analysis.product_brief
        intelligence = analysis.product_intelligence
        angles = project.creative_angles or self.angle_generator.generate(project, brief, intelligence)
        selected_angles = self._select_angles(angles, request.angle_ids, request.variant_count)

        project.product_brief = brief
        project.product_intelligence = intelligence
        project.vision_analysis = analysis.vision_analysis
        project.creative_angles = angles
        project.variants = self.script_generator.generate(project, brief, selected_angles, intelligence)
        self.storage.save_project(project)
        return project.variants

    def render_mock_videos(self, project_id: str) -> Project:
        project = self.storage.get_project(project_id)
        if not project.variants:
            request = GenerateVariantsRequest(variant_count=2)
            self.generate_variants(project_id, request)
            project = self.storage.get_project(project_id)

        project.variants = self.video_provider.render_mock(project, project.variants)
        return self.storage.save_project(project)

    def delete_project(self, project_id: str) -> None:
        self.storage.delete_project(project_id)

    def _ensure_analysis(self, project: Project) -> AnalyzeProjectResponse:
        if project.product_brief and project.product_intelligence:
            return AnalyzeProjectResponse(
                product_intelligence=project.product_intelligence,
                product_brief=project.product_brief,
                vision_analysis=project.vision_analysis
                or VisionAnalysis(detected_product_type=project.product_intelligence.product_type),
            )
        return self.analyzer.analyze(project)

    def _select_angles(
        self,
        angles: list[CreativeAngle],
        angle_ids: list[str] | None,
        variant_count: int,
    ) -> list[CreativeAngle]:
        if angle_ids:
            by_id = {angle.id: angle for angle in angles}
            selected = [by_id[angle_id] for angle_id in angle_ids if angle_id in by_id]
            if not selected:
                raise ValueError("None of the requested angle_ids exist on this project")
            return selected[:variant_count]

        return sorted(angles, key=lambda angle: angle.score, reverse=True)[:variant_count]

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
