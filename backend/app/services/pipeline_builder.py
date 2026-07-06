from pathlib import Path
from typing import Any

from app.models.schemas import (
    PipelineAsset,
    PipelineExpectedOutput,
    PipelineRequiredInput,
    PipelineStep,
    Project,
    UIOverlayItem,
    Variant,
    VariantGenerationPipeline,
)
from app.services.pipeline_manifest import load_pipeline_manifest, stage_contract
from app.services.video_provider import ProviderRegistry


def build_generation_pipeline(project: Project, variant: Variant) -> VariantGenerationPipeline:
    package = variant.production_package
    if package is None:
        raise ValueError("Variant is missing production_package. Generate variants again.")

    manifest = load_pipeline_manifest()
    assets = _project_upload_assets(project)
    steps: list[PipelineStep] = []
    step_number = 1

    for reference_prompt in package.character_reference_prompts:
        output_key = reference_prompt.reference_id
        steps.append(
            PipelineStep(
                step_id=f"character_reference_{output_key}",
                step_number=step_number,
                stage="character_reference",
                title=f"Create {reference_prompt.purpose}",
                goal="Generate one reference image of the same main actor. Change only pose/framing for this reference.",
                tool_type="image_generation",
                execution_mode="manual_or_provider",
                provider_capability="image_generation",
                prompt_to_copy=reference_prompt.prompt,
                negative_prompt_to_copy=reference_prompt.negative_prompt,
                settings={"aspect_ratio": reference_prompt.aspect_ratio, "style": "realistic UGC reference image"},
                expected_outputs=[
                    PipelineExpectedOutput(
                        asset_key=output_key,
                        asset_type="image",
                        label=reference_prompt.purpose,
                        file_name_hint=f"{output_key}.png",
                        required_for_next_steps=_steps_requiring_reference(package.production_scenes, output_key),
                    )
                ],
                manual_instructions=[
                    "Open your image generation tool.",
                    "Paste the prompt and negative prompt.",
                    "Use the exact aspect ratio shown in settings.",
                    "Export one clean image and upload it back to this step.",
                ],
                provider_payload={
                    "prompt": reference_prompt.prompt,
                    "negative_prompt": reference_prompt.negative_prompt,
                    "aspect_ratio": reference_prompt.aspect_ratio,
                },
            )
        )
        step_number += 1

    for scene in package.production_scenes:
        output_key = f"scene_{scene.scene_number}_keyframe"
        steps.append(
            PipelineStep(
                step_id=f"scene_{scene.scene_number}_keyframe",
                step_number=step_number,
                stage="scene_keyframe",
                title=f"Generate scene {scene.scene_number} keyframe",
                goal=scene.creative_objective,
                tool_type="image_generation",
                execution_mode="manual_or_provider",
                provider_capability="image_generation",
                required_inputs=[
                    PipelineRequiredInput(
                        asset_key=asset_key,
                        asset_type="image",
                        label=asset_key.replace("_", " ").title(),
                        required=True,
                        accepted_sources=["uploaded_by_user", "generated_by_provider"],
                        instructions="Use this actor/reference image as input so the generated keyframe keeps the same identity.",
                    )
                    for asset_key in scene.required_reference_assets
                ],
                prompt_to_copy=scene.keyframe_prompt,
                negative_prompt_to_copy=scene.negative_prompt,
                settings={"aspect_ratio": "9:16", "scene_number": scene.scene_number, "global_timeline": _global_timeline(package.production_scenes, scene.scene_number)},
                expected_outputs=[
                    PipelineExpectedOutput(
                        asset_key=output_key,
                        asset_type="image",
                        label=f"Scene {scene.scene_number} keyframe",
                        file_name_hint=f"scene_{scene.scene_number}_keyframe.png",
                        required_for_next_steps=[f"scene_{scene.scene_number}_clip"],
                    )
                ],
                manual_instructions=[
                    "Upload the required character references into your image tool.",
                    "Paste the keyframe prompt.",
                    "Keep phone screens blank or clean for app UI overlay later.",
                    "Upload the generated keyframe image back to this step.",
                ],
                provider_payload={
                    "prompt": scene.keyframe_prompt,
                    "negative_prompt": scene.negative_prompt,
                    "required_reference_assets": scene.required_reference_assets,
                    "aspect_ratio": "9:16",
                },
            )
        )
        step_number += 1

    for scene in package.production_scenes:
        output_key = f"scene_{scene.scene_number}_clip"
        steps.append(
            PipelineStep(
                step_id=f"scene_{scene.scene_number}_clip",
                step_number=step_number,
                stage="video_clip",
                title=f"Animate scene {scene.scene_number}",
                goal=scene.action_description,
                tool_type="video_generation",
                execution_mode="manual_or_provider",
                provider_capability="video_generation",
                required_inputs=[
                    PipelineRequiredInput(
                        asset_key=f"scene_{scene.scene_number}_keyframe",
                        asset_type="image",
                        label=f"Scene {scene.scene_number} keyframe",
                        required=True,
                        accepted_sources=["uploaded_by_user", "generated_by_provider"],
                        instructions="Use this image as the first frame or image-to-video source.",
                    ),
                    *[
                        PipelineRequiredInput(
                            asset_key=asset_key,
                            asset_type="image",
                            label=asset_key.replace("_", " ").title(),
                            required=False,
                            accepted_sources=["uploaded_by_user", "generated_by_provider"],
                            instructions="Use if the video provider supports character/reference images.",
                        )
                        for asset_key in scene.required_reference_assets
                    ],
                ],
                prompt_to_copy=scene.video_prompt,
                negative_prompt_to_copy=scene.negative_prompt,
                motion_instruction=scene.motion_instruction,
                consistency_instruction=scene.consistency_instruction,
                settings={
                    "duration_seconds": min(scene.duration_seconds, 6) if scene.scene_number == 3 else scene.duration_seconds,
                    "aspect_ratio": "9:16",
                    "generation_mode": scene.generation_mode,
                    "global_timeline": _global_timeline(package.production_scenes, scene.scene_number),
                },
                expected_outputs=[
                    PipelineExpectedOutput(
                        asset_key=output_key,
                        asset_type="video",
                        label=f"Scene {scene.scene_number} raw clip",
                        file_name_hint=f"scene_{scene.scene_number}_clip.mp4",
                        required_for_next_steps=[f"scene_{scene.scene_number}_overlay", "assembly_master"],
                    )
                ],
                manual_instructions=[
                    "Open your video generation tool.",
                    "Upload the scene keyframe as image-to-video input.",
                    "Paste the video prompt, motion instruction, and consistency instruction.",
                    "Use the duration/aspect ratio from settings.",
                    "Upload the generated clip back to this step.",
                ],
                provider_payload={
                    "prompt": scene.video_prompt,
                    "negative_prompt": scene.negative_prompt,
                    "motion_instruction": scene.motion_instruction,
                    "consistency_instruction": scene.consistency_instruction,
                    "duration_seconds": scene.duration_seconds,
                    "aspect_ratio": "9:16",
                },
            )
        )
        step_number += 1

    final_scene_asset_keys: list[str] = []
    for scene in package.production_scenes:
        if scene.ui_overlay_plan:
            output_key = f"scene_{scene.scene_number}_with_overlay"
            requires_app_screenshot = any(_is_app_overlay(item) for item in scene.ui_overlay_plan)
            required_inputs = [
                PipelineRequiredInput(
                    asset_key=f"scene_{scene.scene_number}_clip",
                    asset_type="video",
                    label=f"Scene {scene.scene_number} raw clip",
                    required=True,
                    accepted_sources=["uploaded_by_user", "generated_by_provider"],
                    instructions="Use this raw clip as the base layer for overlays.",
                )
            ]
            if requires_app_screenshot:
                required_inputs.append(
                    PipelineRequiredInput(
                        asset_key="app_screenshot",
                        asset_type="app_screenshot",
                        label="App screenshot",
                        required=True,
                        accepted_sources=["project_upload", "uploaded_by_user"],
                        instructions="Use the uploaded app screenshot and overlay it onto the blank phone screen.",
                    )
                )

            steps.append(
                PipelineStep(
                    step_id=f"scene_{scene.scene_number}_overlay",
                    step_number=step_number,
                    stage="app_ui_overlay",
                    title=f"Add overlays to scene {scene.scene_number}",
                    goal="Add readable UI, captions, disclaimers, CTA, and other editor overlays after video generation.",
                    tool_type="video_editing",
                    execution_mode="manual_or_provider",
                    provider_capability="video_editing",
                    required_inputs=required_inputs,
                    settings={
                        "overlay_plan": [_normalize_overlay(item).model_dump(mode="json") for item in scene.ui_overlay_plan],
                        "global_timeline": _global_timeline(package.production_scenes, scene.scene_number),
                    },
                    expected_outputs=[
                        PipelineExpectedOutput(
                            asset_key=output_key,
                            asset_type="video",
                            label=f"Scene {scene.scene_number} clip with overlays",
                            file_name_hint=f"scene_{scene.scene_number}_with_overlay.mp4",
                            required_for_next_steps=["assembly_master"],
                        )
                    ],
                    manual_instructions=[
                        "Open your editor or video editing tool.",
                        "Overlay the app screenshot onto the blank phone screen if this scene uses app UI.",
                        "Keep generated video free of fake app text; app UI should be readable editor overlay.",
                        "Add subtitles, disclaimer, logo, CTA, or highlight overlays using the overlay plan.",
                        "Upload the finished scene clip back to this step.",
                    ],
                    provider_payload={
                        "overlay_plan": [_normalize_overlay(item).model_dump(mode="json") for item in scene.ui_overlay_plan],
                        "base_clip_asset_key": f"scene_{scene.scene_number}_clip",
                    },
                )
            )
            final_scene_asset_keys.append(output_key)
            step_number += 1
        else:
            final_scene_asset_keys.append(f"scene_{scene.scene_number}_clip")

    steps.append(
        PipelineStep(
            step_id="assembly_master",
            step_number=step_number,
            stage="assembly",
            title="Assemble final master video",
            goal="Cut all completed scene clips into one master ad and add final audio/subtitles.",
            tool_type="final_assembly",
            execution_mode="manual_or_provider",
            provider_capability="final_assembly",
            required_inputs=[
                PipelineRequiredInput(
                    asset_key=asset_key,
                    asset_type="video",
                    label=asset_key.replace("_", " ").title(),
                    required=True,
                    accepted_sources=["uploaded_by_user", "generated_by_provider"],
                    instructions="Use this completed scene clip in the final cut sequence.",
                )
                for asset_key in final_scene_asset_keys
            ],
            settings=package.edit_plan.model_dump(mode="json"),
            expected_outputs=[
                PipelineExpectedOutput(
                    asset_key="final_video_master",
                    asset_type="video",
                    label="Final master video",
                    file_name_hint="final_video_master.mp4",
                    required_for_next_steps=["export_9x16", "export_1x1"],
                )
            ],
            manual_instructions=[
                "Import every completed scene clip into your editor.",
                "Cut clips in the order defined by the edit plan.",
                "Add music, subtitles, disclaimers, and CTA overlays if not already applied.",
                "Upload the master video back to this step.",
            ],
            provider_payload={
                "scene_asset_keys": final_scene_asset_keys,
                "edit_plan": package.edit_plan.model_dump(mode="json"),
            },
        )
    )
    step_number += 1

    for ratio in ("9:16", "1:1"):
        suffix = ratio.replace(":", "x")
        steps.append(
            PipelineStep(
                step_id=f"export_{suffix}",
                step_number=step_number,
                stage="export",
                title=f"Export {ratio}",
                goal=f"Create final {ratio} deliverable for ad placement.",
                tool_type="export",
                execution_mode="manual_or_provider",
                provider_capability="export",
                required_inputs=[
                    PipelineRequiredInput(
                        asset_key="final_video_master",
                        asset_type="video",
                        label="Final master video",
                        required=True,
                        accepted_sources=["uploaded_by_user", "generated_by_provider"],
                        instructions="Use the master video as the source for this export ratio.",
                    )
                ],
                settings={"aspect_ratio": ratio},
                expected_outputs=[
                    PipelineExpectedOutput(
                        asset_key=f"final_video_{suffix}",
                        asset_type="video",
                        label=f"Final video {ratio}",
                        file_name_hint=f"final_video_{suffix}.mp4",
                        required_for_next_steps=[],
                    )
                ],
                manual_instructions=[
                    f"Resize or crop the master video for {ratio}.",
                    "Check that captions, app UI overlays, and CTA remain readable.",
                    "Upload the final exported video back to this step.",
                ],
                provider_payload={"source_asset_key": "final_video_master", "aspect_ratio": ratio},
            )
        )
        step_number += 1

    provider_contracts = ProviderRegistry(requirements=list(manifest.get("provider_requirements", []))).contracts()
    pipeline = VariantGenerationPipeline(
        variant_id=variant.id,
        pipeline_name=str(manifest.get("name", "ad_video_generation")),
        pipeline_version=str(manifest.get("version", "1.0")),
        objective=str(manifest.get("objective", "")),
        source_artifacts=list(manifest.get("source_artifacts", [])),
        stage_contracts=list(manifest.get("stages", [])),
        provider_contracts=provider_contracts,
        assets=assets,
        steps=steps,
    )
    _apply_manifest_contracts(pipeline, manifest)
    _recompute_step_statuses(pipeline)
    return pipeline


def enrich_generation_pipeline(pipeline: VariantGenerationPipeline) -> VariantGenerationPipeline:
    manifest = load_pipeline_manifest()
    pipeline.pipeline_name = str(manifest.get("name", pipeline.pipeline_name))
    pipeline.pipeline_version = str(manifest.get("version", pipeline.pipeline_version))
    pipeline.objective = str(manifest.get("objective", pipeline.objective))
    pipeline.source_artifacts = list(manifest.get("source_artifacts", pipeline.source_artifacts))
    pipeline.stage_contracts = list(manifest.get("stages", pipeline.stage_contracts))
    pipeline.provider_contracts = ProviderRegistry(requirements=list(manifest.get("provider_requirements", []))).contracts()
    _apply_manifest_contracts(pipeline, manifest)
    _recompute_step_statuses(pipeline)
    return pipeline


def _project_upload_assets(project: Project) -> list[PipelineAsset]:
    assets: list[PipelineAsset] = []
    app_screenshot_added = False
    for upload in project.uploaded_files:
        asset_type = _infer_uploaded_asset_type(upload.file_name, upload.content_type)
        asset_key = f"project_upload_{upload.id}"
        assets.append(
            PipelineAsset(
                asset_key=asset_key,
                asset_type=asset_type,
                label=upload.file_name,
                url=upload.url,
                path=upload.path,
                source="project_upload",
                metadata={"content_type": upload.content_type, "size_bytes": upload.size_bytes},
            )
        )
        if asset_type == "app_screenshot" and not app_screenshot_added:
            assets.append(
                PipelineAsset(
                    asset_key="app_screenshot",
                    asset_type="app_screenshot",
                    label=f"App screenshot: {upload.file_name}",
                    url=upload.url,
                    path=upload.path,
                    source="project_upload",
                    metadata={"alias_for": asset_key, "content_type": upload.content_type, "size_bytes": upload.size_bytes},
                )
            )
            app_screenshot_added = True
    return assets


def _infer_uploaded_asset_type(file_name: str, content_type: str | None) -> str:
    lowered = file_name.lower()
    if content_type and content_type.startswith("video/"):
        return "video"
    if content_type and content_type.startswith("audio/"):
        return "audio"
    if "app" in lowered or "screenshot" in lowered or "screen" in lowered or "mobile" in lowered:
        return "app_screenshot"
    if content_type and content_type.startswith("image/"):
        return "image"
    suffix = Path(file_name).suffix.lower()
    if suffix in {".mp4", ".mov", ".webm"}:
        return "video"
    if suffix in {".json"}:
        return "json"
    if suffix in {".zip"}:
        return "zip"
    return "image"


def _steps_requiring_reference(scenes: list[Any], reference_id: str) -> list[str]:
    return [
        f"scene_{scene.scene_number}_keyframe"
        for scene in scenes
        if reference_id in scene.required_reference_assets
    ]


def _global_timeline(scenes: list[Any], scene_number: int) -> dict[str, float]:
    start = 0.0
    for scene in scenes:
        end = start + float(scene.duration_seconds)
        if scene.scene_number == scene_number:
            return {"start_seconds": start, "end_seconds": end}
        start = end
    return {"start_seconds": 0, "end_seconds": 0}


def _is_app_overlay(item: UIOverlayItem) -> bool:
    return item.overlay_type in {"app_screen", "app_screen_overlay"}


def _normalize_overlay(item: UIOverlayItem) -> UIOverlayItem:
    if item.overlay_type != "app_screen":
        return item
    return item.model_copy(update={"overlay_type": "app_screen_overlay"})


def _recompute_step_statuses(pipeline: VariantGenerationPipeline) -> None:
    asset_keys = {asset.asset_key for asset in pipeline.assets}
    any_completed = False
    any_failed = False
    for step in pipeline.steps:
        if step.output_assets:
            step.status = "completed"
            asset_keys.update(asset.asset_key for asset in step.output_assets)
            any_completed = True
            continue
        if step.status == "failed":
            any_failed = True
            continue
        required_keys = [item.asset_key for item in step.required_inputs if item.required]
        step.status = "ready" if all(asset_key in asset_keys for asset_key in required_keys) else "pending"

    if any_failed:
        pipeline.status = "failed"
    elif pipeline.steps and all(step.status in {"completed", "skipped"} for step in pipeline.steps):
        pipeline.status = "completed"
    elif any_completed or any(step.status == "ready" for step in pipeline.steps):
        pipeline.status = "in_progress"
    else:
        pipeline.status = "draft"


def _apply_manifest_contracts(pipeline: VariantGenerationPipeline, manifest: dict[str, Any]) -> None:
    contracts_by_tool = {
        contract.get("tool_type"): contract
        for contract in pipeline.provider_contracts
        if contract.get("tool_type")
    }
    for step in pipeline.steps:
        contract = stage_contract(manifest, step.stage)
        if contract:
            step.stage_label = str(contract.get("label") or step.stage)
            step.stage_purpose = str(contract.get("purpose") or "")
            step.source_artifacts = list(contract.get("required_artifacts_in") or [])
            step.review_focus = list(contract.get("review_focus") or [])
            step.success_criteria = list(contract.get("success_criteria") or [])
            step.provider_capability = step.provider_capability or str(contract.get("provider_capability") or step.tool_type)
            if contract.get("manual_goal"):
                step.settings.setdefault("manual_goal", contract["manual_goal"])

        provider_contract = contracts_by_tool.get(step.tool_type)
        if provider_contract:
            step.provider_options = [provider_contract]
        step.provider_payload.setdefault("source_artifacts", step.source_artifacts)
        step.provider_payload.setdefault("success_criteria", step.success_criteria)
