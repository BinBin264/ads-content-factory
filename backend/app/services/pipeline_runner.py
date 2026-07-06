from app.models.schemas import PipelineAsset, Project, Variant
from app.services.pipeline_asset_service import PipelineAssetService
from app.services.video_provider import ProviderRegistry, VideoProviderError


class PipelineRunner:
    def __init__(
        self,
        asset_service: PipelineAssetService | None = None,
        provider_registry: ProviderRegistry | None = None,
    ) -> None:
        self.asset_service = asset_service or PipelineAssetService()
        self.provider_registry = provider_registry or ProviderRegistry()

    def run_step(self, project: Project, variant_id: str, step_id: str) -> Project:
        variant = self._get_variant(project, variant_id)
        pipeline = self.asset_service.ensure_pipeline(project, variant_id)
        step = self._get_step(variant, step_id)

        if step.output_assets:
            self.asset_service.recompute_ready_steps(pipeline)
            return project
        if step.status not in {"ready", "failed"}:
            self.asset_service.input_assets_for_step(pipeline, step_id)

        input_assets = self.asset_service.input_assets_for_step(pipeline, step_id)
        provider = self.provider_registry.get_provider(step.tool_type)
        if provider is None:
            message = "Video provider is not configured. Set VIDEO_PROVIDER_NAME and VIDEO_PROVIDER_API_KEY."
            self.asset_service.mark_step_failed(pipeline, step_id, message)
            raise VideoProviderError(message)

        step.status = "running"
        step.error_message = None
        try:
            output_asset = self._call_provider(provider, step.tool_type, step, input_assets)
        except VideoProviderError as exc:
            self.asset_service.mark_step_failed(pipeline, step_id, str(exc))
            raise
        except Exception as exc:  # pragma: no cover - external provider safety
            message = f"Provider for {step.tool_type} failed. {exc}"
            self.asset_service.mark_step_failed(pipeline, step_id, message)
            raise VideoProviderError(message) from exc

        self.asset_service.attach_provider_asset(pipeline=pipeline, step_id=step_id, asset=output_asset)
        self._sync_variant_video_urls(variant)
        return project

    def run_pipeline(self, project: Project, variant_id: str) -> Project:
        variant = self._get_variant(project, variant_id)
        pipeline = self.asset_service.ensure_pipeline(project, variant_id)
        while True:
            self.asset_service.recompute_ready_steps(pipeline)
            ready_steps = [step for step in pipeline.steps if step.status == "ready"]
            if not ready_steps:
                break
            self.run_step(project, variant.id, ready_steps[0].step_id)

        self.asset_service.recompute_ready_steps(pipeline)
        self._sync_variant_video_urls(variant)
        return project

    def run_all_variants(self, project: Project) -> Project:
        if not project.variants:
            raise ValueError("Generate variants before rendering video")
        for variant in project.variants:
            self.run_pipeline(project, variant.id)
        return project

    def _call_provider(self, provider, tool_type: str, step, input_assets: list[PipelineAsset]) -> PipelineAsset:
        if tool_type == "image_generation":
            return provider.generate_image(step, input_assets)
        if tool_type == "video_generation":
            return provider.generate_video(step, input_assets)
        if tool_type in {"image_editing", "video_editing"}:
            return provider.apply_overlay(step, input_assets)
        if tool_type == "final_assembly":
            return provider.assemble(step, input_assets)
        if tool_type == "export":
            return provider.export(step, input_assets)
        raise VideoProviderError("Video provider is not configured. Set VIDEO_PROVIDER_NAME and VIDEO_PROVIDER_API_KEY.")

    def _get_variant(self, project: Project, variant_id: str) -> Variant:
        for variant in project.variants:
            if variant.id == variant_id:
                return variant
        raise ValueError(f"Variant '{variant_id}' was not found on this project.")

    def _get_step(self, variant: Variant, step_id: str):
        if variant.generation_pipeline is None:
            raise ValueError("Variant is missing generation_pipeline. Generate variants again.")
        for step in variant.generation_pipeline.steps:
            if step.step_id == step_id:
                return step
        raise ValueError(f"Pipeline step '{step_id}' was not found.")

    def _sync_variant_video_urls(self, variant: Variant) -> None:
        pipeline = variant.generation_pipeline
        if pipeline is None:
            return

        by_key = {asset.asset_key: asset for asset in pipeline.assets}
        for step in pipeline.steps:
            for asset in step.output_assets:
                by_key[asset.asset_key] = asset

        master = by_key.get("final_video_master")
        export_9x16 = by_key.get("final_video_9x16")
        export_1x1 = by_key.get("final_video_1x1")
        if master and master.url:
            variant.video_url = master.url
        if export_9x16 and export_9x16.url:
            variant.export_9x16_url = export_9x16.url
        if export_1x1 and export_1x1.url:
            variant.export_1x1_url = export_1x1.url
        if pipeline.status == "completed":
            variant.video_status = "ready"
        elif pipeline.status == "failed":
            variant.video_status = "failed"
        elif pipeline.status == "in_progress":
            variant.video_status = "rendering"
