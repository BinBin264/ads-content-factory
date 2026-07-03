import json
import zipfile
from pathlib import Path

from fastapi import UploadFile

from app.config import OUTPUTS_DIR
from app.models.schemas import AnalyzeProjectResponse, CreativeAngle, GenerateVariantsRequest, ProductBrief, Project, Variant, VisionAnalysis
from app.services.angle_generator import CreativeAngleGenerator, GeminiCreativeAngleGenerator
from app.services.product_analyzer import ProductAnalyzer, ProductIntelligenceAnalyzer
from app.services.script_generator import GeminiVariantScriptGenerator, VariantScriptGenerator
from app.services.storage_service import JsonProjectStorage, LocalFileStorage
from app.services.video_provider import ExternalVideoProvider, VideoProvider


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
        self.analyzer = analyzer or ProductIntelligenceAnalyzer()
        self.angle_generator = angle_generator or GeminiCreativeAngleGenerator()
        self.script_generator = script_generator or GeminiVariantScriptGenerator()
        self.video_provider = video_provider or ExternalVideoProvider()

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

    def render_videos(self, project_id: str) -> Project:
        project = self.storage.get_project(project_id)
        if not project.variants:
            raise ValueError("Generate variants before rendering video")

        project.variants = self.video_provider.render(project, project.variants)
        return self.storage.save_project(project)

    def export_production_package(self, project_id: str) -> Project:
        project = self.storage.get_project(project_id)
        if not project.variants:
            raise ValueError("Generate variants before exporting a production package")

        for variant in project.variants:
            if not variant.production_package:
                raise ValueError("Generate variants again to create a production package")
            variant_dir = OUTPUTS_DIR / project.id / variant.id
            variant_dir.mkdir(parents=True, exist_ok=True)
            self._write_variant_package_files(variant_dir, variant)
            zip_path = self._zip_variant_package(variant_dir)
            variant.video_status = "package_exported"
            variant.export_package_url = self._output_url(zip_path)

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
            selected_ids = {angle.id for angle in selected}
            remaining = [
                angle
                for angle in sorted(angles, key=lambda angle: angle.score, reverse=True)
                if angle.id not in selected_ids
            ]
            return (selected + remaining)[:variant_count]

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

    def _write_variant_package_files(self, variant_dir: Path, variant: Variant) -> None:
        package = variant.production_package
        if package is None:
            raise ValueError("Variant is missing production_package")

        self._write_json(variant_dir / "character_bible.json", package.character_bible.model_dump(mode="json"))
        self._write_text(
            variant_dir / "character_reference_prompts.txt",
            "\n\n".join(
                [
                    f"{prompt.reference_id} ({prompt.aspect_ratio})\nPurpose: {prompt.purpose}\nPrompt:\n{prompt.prompt}\nNegative:\n{prompt.negative_prompt}\nNotes: {prompt.notes}"
                    for prompt in package.character_reference_prompts
                ]
            ),
        )
        self._write_json(variant_dir / "production_scenes.json", [scene.model_dump(mode="json") for scene in package.production_scenes])
        self._write_text(
            variant_dir / "keyframe_prompts.txt",
            "\n\n".join([f"Scene {scene.scene_number}\n{scene.keyframe_prompt}" for scene in package.production_scenes]),
        )
        self._write_text(
            variant_dir / "video_prompts.txt",
            "\n\n".join([f"Scene {scene.scene_number}\n{scene.video_prompt}" for scene in package.production_scenes]),
        )
        self._write_text(
            variant_dir / "ui_overlay_plan.txt",
            "\n\n".join(
                [
                    f"Scene {scene.scene_number}\n"
                    + "\n".join(
                        [
                            f"- {item.overlay_type}: {item.text} ({item.start_time}-{item.end_time}, {item.position}) | {item.style_notes} | {item.safety_notes}"
                            for item in scene.ui_overlay_plan
                        ]
                    )
                    for scene in package.production_scenes
                ]
            ),
        )
        self._write_text(
            variant_dir / "edit_plan.txt",
            json.dumps(package.edit_plan.model_dump(mode="json"), ensure_ascii=False, indent=2),
        )
        self._write_text(variant_dir / "script.txt", variant.script)
        self._write_json(variant_dir / "storyboard.json", [scene.model_dump(mode="json") for scene in variant.storyboard])
        self._write_text(variant_dir / "caption.txt", f"{variant.title}\n\n{variant.caption}\n\nCover prompt:\n{variant.cover_prompt}")

    def _zip_variant_package(self, variant_dir: Path) -> Path:
        zip_path = variant_dir / "production_package.zip"
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for path in variant_dir.iterdir():
                if path == zip_path or not path.is_file():
                    continue
                archive.write(path, arcname=path.name)
        return zip_path

    def _write_json(self, path: Path, data: object) -> None:
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def _write_text(self, path: Path, content: str) -> None:
        path.write_text(content, encoding="utf-8")

    def _output_url(self, path: Path) -> str:
        relative = path.relative_to(OUTPUTS_DIR).as_posix()
        return f"/outputs/{relative}"
