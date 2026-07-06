from pathlib import Path
from typing import Any

from fastapi import UploadFile

from app.config import OUTPUTS_DIR
from app.models.schemas import PipelineAsset, Project, Variant, VariantGenerationPipeline
from app.services.pipeline_builder import _project_upload_assets, build_generation_pipeline, enrich_generation_pipeline


def _sanitize_filename(filename: str) -> str:
    safe = "".join(ch if ch.isalnum() or ch in {".", "-", "_"} else "_" for ch in filename)
    return safe.strip("._") or "asset"


class PipelineAssetService:
    async def upload_step_result(
        self,
        *,
        project: Project,
        variant_id: str,
        step_id: str,
        file: UploadFile,
        asset_key: str | None = None,
        notes: str | None = None,
    ) -> Project:
        variant = self._get_variant(project, variant_id)
        pipeline = self._ensure_pipeline(project, variant)
        step = self._get_step(pipeline, step_id)

        resolved_asset_key = asset_key or self._default_asset_key(step)
        asset_dir = OUTPUTS_DIR / project.id / variant.id / "assets"
        asset_dir.mkdir(parents=True, exist_ok=True)
        original_name = file.filename or f"{resolved_asset_key}.bin"
        destination = asset_dir / f"{resolved_asset_key}_{_sanitize_filename(original_name)}"
        content = await file.read()
        destination.write_bytes(content)
        await file.close()

        asset = PipelineAsset(
            asset_key=resolved_asset_key,
            asset_type=self._infer_asset_type(original_name, file.content_type),
            label=original_name,
            url=f"/outputs/{project.id}/{variant.id}/assets/{destination.name}",
            path=str(destination),
            source="uploaded_by_user",
            source_step_id=step_id,
            metadata={"content_type": file.content_type, "size_bytes": len(content), "notes": notes or ""},
        )
        self._upsert_asset(pipeline.assets, asset)
        self._upsert_asset(step.output_assets, asset)
        step.status = "completed"
        step.error_message = None
        self.recompute_ready_steps(pipeline)
        return project

    def ensure_pipeline(self, project: Project, variant_id: str) -> VariantGenerationPipeline:
        variant = self._get_variant(project, variant_id)
        return self._ensure_pipeline(project, variant)

    def recompute_ready_steps(self, pipeline: VariantGenerationPipeline) -> None:
        available_asset_keys = {asset.asset_key for asset in pipeline.assets}
        any_completed = False
        any_failed = False

        for step in pipeline.steps:
            if step.output_assets:
                step.status = "completed"
                available_asset_keys.update(asset.asset_key for asset in step.output_assets)
                any_completed = True
                continue
            if step.status == "failed":
                any_failed = True
                continue
            if step.status == "running":
                continue

            required_keys = [item.asset_key for item in step.required_inputs if item.required]
            step.status = "ready" if all(asset_key in available_asset_keys for asset_key in required_keys) else "pending"

        if any_failed:
            pipeline.status = "failed"
        elif pipeline.steps and all(step.status in {"completed", "skipped"} for step in pipeline.steps):
            pipeline.status = "completed"
        elif any_completed or any(step.status in {"ready", "running"} for step in pipeline.steps):
            pipeline.status = "in_progress"
        else:
            pipeline.status = "draft"

    def find_asset(self, pipeline: VariantGenerationPipeline, asset_key: str) -> PipelineAsset | None:
        for asset in pipeline.assets:
            if asset.asset_key == asset_key:
                return asset
        for step in pipeline.steps:
            for asset in step.output_assets:
                if asset.asset_key == asset_key:
                    return asset
        return None

    def input_assets_for_step(self, pipeline: VariantGenerationPipeline, step_id: str) -> list[PipelineAsset]:
        step = self._get_step(pipeline, step_id)
        assets: list[PipelineAsset] = []
        for required_input in step.required_inputs:
            asset = self.find_asset(pipeline, required_input.asset_key)
            if asset:
                assets.append(asset)
            elif required_input.required:
                raise ValueError(f"Step '{step_id}' is missing required input asset '{required_input.asset_key}'.")
        return assets

    def attach_provider_asset(
        self,
        *,
        pipeline: VariantGenerationPipeline,
        step_id: str,
        asset: PipelineAsset,
    ) -> None:
        step = self._get_step(pipeline, step_id)
        self._upsert_asset(pipeline.assets, asset)
        self._upsert_asset(step.output_assets, asset)
        step.status = "completed"
        step.error_message = None
        self.recompute_ready_steps(pipeline)

    def mark_step_failed(self, pipeline: VariantGenerationPipeline, step_id: str, message: str) -> None:
        step = self._get_step(pipeline, step_id)
        step.status = "failed"
        step.error_message = message
        pipeline.status = "failed"

    def _ensure_pipeline(self, project: Project, variant: Variant) -> VariantGenerationPipeline:
        if variant.generation_pipeline is None:
            variant.generation_pipeline = build_generation_pipeline(project, variant)
        else:
            enrich_generation_pipeline(variant.generation_pipeline)
            self._ensure_project_upload_assets(project, variant.generation_pipeline)
            self.recompute_ready_steps(variant.generation_pipeline)
        return variant.generation_pipeline

    def _ensure_project_upload_assets(self, project: Project, pipeline: VariantGenerationPipeline) -> None:
        if any(asset.source == "project_upload" for asset in pipeline.assets):
            return
        for asset in _project_upload_assets(project):
            self._upsert_asset(pipeline.assets, asset)

    def _get_variant(self, project: Project, variant_id: str) -> Variant:
        for variant in project.variants:
            if variant.id == variant_id:
                return variant
        raise ValueError(f"Variant '{variant_id}' was not found on this project.")

    def _get_step(self, pipeline: VariantGenerationPipeline, step_id: str):
        for step in pipeline.steps:
            if step.step_id == step_id:
                return step
        raise ValueError(f"Pipeline step '{step_id}' was not found.")

    def _default_asset_key(self, step: Any) -> str:
        if not step.expected_outputs:
            raise ValueError(f"Pipeline step '{step.step_id}' has no expected output asset.")
        return step.expected_outputs[0].asset_key

    def _upsert_asset(self, assets: list[PipelineAsset], asset: PipelineAsset) -> None:
        for index, existing in enumerate(assets):
            if existing.asset_key == asset.asset_key:
                assets[index] = asset
                return
        assets.append(asset)

    def _infer_asset_type(self, file_name: str, content_type: str | None):
        lowered = file_name.lower()
        if content_type and content_type.startswith("video/"):
            return "video"
        if content_type and content_type.startswith("audio/"):
            return "audio"
        if "subtitle" in lowered or lowered.endswith((".srt", ".vtt")):
            return "subtitle"
        if lowered.endswith(".json"):
            return "json"
        if lowered.endswith(".zip"):
            return "zip"
        if "app" in lowered or "screenshot" in lowered or "screen" in lowered or "mobile" in lowered:
            return "app_screenshot"
        return "image"
