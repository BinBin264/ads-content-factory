from collections.abc import Callable

from fastapi import UploadFile

from app.models.schemas import (
    CreativePlan,
    Project,
    ReviewSceneTakeRequest,
    RewriteSceneRequest,
    SelectKeyframeCandidateRequest,
    UpdateKeyframePromptSlotRequest,
    UpdateProductReferenceRequest,
    UpdateProjectRequest,
    UpdateReferenceAssetRequest,
    UpdateSceneRequest,
    UpdateSceneVideoPromptRequest,
)
from app.services.creative_plan_generator import CreativePlanGenerator, GeminiCreativePlanGenerator
from app.services.image_provider import ImageReference, OpenAICompatibleImageProvider
from app.services.llm_provider import LLMProvider, build_llm_provider
from app.services.production_orchestrator import ProductionOrchestrator
from app.services.storage_service import JsonProjectStorage, LocalFileStorage
from app.services.video_provider import (
    GeneratedVideo,
    ShopAIKeyVideoProvider,
    VideoProviderError,
    VideoReferenceInput,
    VideoReferenceUpload,
    VideoTaskFailedError,
)


DEFAULT_SCENE_CLIP_SECONDS = 8
ALLOWED_SCENE_CLIP_SECONDS = (4, 6, 8, 10)
KEYFRAMES_PER_SCENE = 1
ImageProgressCallback = Callable[[int, str], None]


class ProjectService:
    def __init__(
        self,
        storage: JsonProjectStorage | None = None,
        file_storage: LocalFileStorage | None = None,
        creative_plan_generator: CreativePlanGenerator | None = None,
        llm_provider: LLMProvider | None = None,
        image_provider: OpenAICompatibleImageProvider | None = None,
        video_provider: ShopAIKeyVideoProvider | None = None,
    ) -> None:
        self.storage = storage or JsonProjectStorage()
        self.file_storage = file_storage or LocalFileStorage()
        self.creative_plan_generator = creative_plan_generator or GeminiCreativePlanGenerator()
        self.llm_provider = llm_provider or build_llm_provider()
        self.image_provider = image_provider or OpenAICompatibleImageProvider()
        self.video_provider = video_provider or ShopAIKeyVideoProvider()
        self.production_orchestrator = ProductionOrchestrator()

    async def create_project(
        self,
        *,
        product_name: str,
        workflow_type: str,
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
            workflow_type=workflow_type,
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
        project.uploaded_files = await self.file_storage.save_product_uploads(project.id, files, start_index=1)
        return self.storage.save_project(project)

    async def upload_project_files(self, project_id: str, files: list[UploadFile] | None) -> Project:
        if not files:
            raise ValueError("Select at least one file to upload.")
        project = self.storage.get_project(project_id)
        project.uploaded_files.extend(
            await self.file_storage.save_product_uploads(
                project.id,
                files,
                start_index=self._next_product_reference_index(project),
            )
        )
        return self.storage.save_project(project)

    async def upload_reference_asset_image(self, project_id: str, asset_type: str, file: UploadFile | None) -> Project:
        if file is None:
            raise ValueError("Select one image to upload.")
        project = self.storage.get_project(project_id)
        plan = self._require_plan(project)
        normalized_type = asset_type.lower().strip()
        if normalized_type not in {"character", "location"}:
            raise ValueError("asset_type must be character or location.")

        output_filename = f"{normalized_type}_reference.png"
        saved = await self.file_storage.save_named_upload(project.id, file, output_filename)
        self._replace_reference_asset_file(project, plan.primaryCharacter if normalized_type == "character" else plan.primaryLocation, saved)
        asset = plan.primaryCharacter if normalized_type == "character" else plan.primaryLocation
        project.uploaded_files.append(saved)
        asset["imageUrl"] = saved.url
        asset["status"] = "ready"
        asset["uploadedFileId"] = saved.id
        asset["candidateImages"] = [saved.url]
        project.creative_plan = plan
        return self.storage.save_project(project)

    def list_projects(self) -> list[Project]:
        return sorted(self.storage.list_projects(), key=lambda item: item.created_at, reverse=True)

    def get_project(self, project_id: str) -> Project:
        project = self.storage.get_project(project_id)
        if project.creative_plan and not project.creative_plan.sequenceState:
            project.creative_plan = self.production_orchestrator.prepare_plan(project, project.creative_plan)
            return self.storage.save_project(project)
        return project

    def update_project(self, project_id: str, payload: UpdateProjectRequest) -> Project:
        project = self.storage.get_project(project_id)
        values = payload.model_dump(exclude_unset=True)
        if "product_description" in values:
            project.product_description = self._clean_optional(values.get("product_description"))
        if "brief" in values:
            project.brief = self._clean_optional(values.get("brief"))
        return self.storage.save_project(project)

    def generate_plan_creation(self, project_id: str) -> CreativePlan:
        project = self.storage.get_project(project_id)
        if self._reset_plan_generated_assets(project):
            project = self.storage.save_project(project)
        result = self.creative_plan_generator.create(project)
        if result.creative_plan is None:
            raise ValueError("Plan Creation generation did not return a creative_plan.")
        project.vision_analysis = result.vision_analysis
        project.creative_plan = self.production_orchestrator.prepare_plan(project, result.creative_plan)
        self.storage.save_project(project)
        return project.creative_plan

    def update_product_reference(
        self,
        project_id: str,
        reference_id: str,
        payload: UpdateProductReferenceRequest,
    ) -> Project:
        project = self.storage.get_project(project_id)
        plan = self._require_plan(project)
        references = plan.productReferences
        target = self._find_reference(references, reference_id)
        values = payload.model_dump(exclude_unset=True)
        for key, value in values.items():
            if value is not None:
                target[key] = value
        if values.get("isPrimary") is True:
            for reference in references:
                reference["isPrimary"] = reference is target
        project.creative_plan = plan
        return self.storage.save_project(project)

    def update_scene(
        self,
        project_id: str,
        scene_index: int,
        payload: UpdateSceneRequest,
    ) -> Project:
        project = self.storage.get_project(project_id)
        plan = self._require_plan(project)
        scene = self._find_scene(plan.scenes, scene_index)
        values = payload.model_dump(exclude_unset=True)

        keyframe_relevant = False
        final_prompt_relevant = False
        scalar_fields = [
            "title",
            "visualAction",
            "productMoment",
            "characterAction",
            "locationUse",
            "ambientAudio",
            "onScreenText",
            "keyframePrompt",
        ]
        for key in scalar_fields:
            if key in values:
                scene[key] = values[key]
                final_prompt_relevant = True
                if key in {"title", "visualAction", "productMoment", "characterAction", "locationUse", "keyframePrompt"}:
                    keyframe_relevant = True

        if "voiceLine" in values:
            scene["voiceLines"] = [{"speaker": "Primary actor", "line": values["voiceLine"]}] if values["voiceLine"] else []
            final_prompt_relevant = True
        if "voiceLines" in values and values["voiceLines"] is not None:
            scene["voiceLines"] = self._normalize_voice_lines(values["voiceLines"])
            final_prompt_relevant = True

        camera = dict(scene.get("camera") or {})
        camera_changed = False
        camera_mapping = {
            "cameraShot": "shot",
            "cameraMovement": "movement",
            "composition": "composition",
        }
        for input_key, camera_key in camera_mapping.items():
            if input_key in values:
                camera[camera_key] = values[input_key]
                camera_changed = True
        if camera_changed:
            camera.setdefault("selected", camera.get("shot") or "medium shot")
            camera.setdefault("alternatives", [])
            scene["camera"] = camera
            keyframe_relevant = True
            final_prompt_relevant = True

        if keyframe_relevant:
            scene["keyframePromptStale"] = True
            for slot in scene.get("keyframePrompts") or []:
                if isinstance(slot, dict):
                    slot["stale"] = True
        if final_prompt_relevant:
            scene["finalVideoPromptStale"] = True

        self.production_orchestrator.refresh_scene(plan, scene, compile_prompt=False)

        project.creative_plan = plan
        return self.storage.save_project(project)

    def rewrite_scene(self, project_id: str, scene_index: int, payload: RewriteSceneRequest) -> Project:
        if not payload.instruction.strip():
            raise ValueError("Rewrite instruction is required.")
        project = self.storage.get_project(project_id)
        plan = self._require_plan(project)
        scene = self._find_scene(plan.scenes, scene_index)
        prompt = self._build_rewrite_scene_prompt(project, plan, scene, payload.instruction)
        rewritten = self._llm_provider_for_project(project).generate_json(prompt, temperature=0.35)
        updated = self._coerce_scene(rewritten, scene_index, scene)
        plan.scenes[plan.scenes.index(scene)] = updated
        self.production_orchestrator.refresh_scene(plan, updated, compile_prompt=True)
        project.creative_plan = plan
        return self.storage.save_project(project)

    def update_scene_video_prompt(
        self,
        project_id: str,
        scene_index: int,
        payload: UpdateSceneVideoPromptRequest,
    ) -> Project:
        if not payload.finalVideoPrompt.strip():
            raise ValueError("finalVideoPrompt is required.")
        project = self.storage.get_project(project_id)
        plan = self._require_plan(project)
        scene = self._find_scene(plan.scenes, scene_index)
        final_prompt = payload.finalVideoPrompt.strip()
        if final_prompt != str(scene.get("finalVideoPrompt") or "").strip():
            scene["videoUrl"] = None
            scene["videoJobId"] = None
            scene["videoError"] = None
            scene["videoStatusPayload"] = None
            scene["videoReferenceUploads"] = []
            scene["status"] = "KEYFRAME_READY"
        scene["finalVideoPrompt"] = final_prompt
        scene["finalVideoPromptStale"] = False
        scene["promptQuality"] = self.production_orchestrator.lint_scene_prompt(scene, final_prompt)
        project.creative_plan = plan
        return self.storage.save_project(project)

    def regenerate_scene_video_prompt(self, project_id: str, scene_index: int) -> Project:
        project = self.storage.get_project(project_id)
        plan = self._require_plan(project)
        scene = self._find_scene(plan.scenes, scene_index)
        prompt = self._build_regenerate_final_prompt(project, plan, scene)
        data = self._llm_provider_for_project(project).generate_json(prompt, temperature=0.25)
        final_prompt = str(data.get("finalVideoPrompt") or "").strip()
        if not final_prompt:
            raise ValueError("Gemini did not return finalVideoPrompt.")
        scene["sourceVideoPrompt"] = self._clean_video_prompt(final_prompt)
        scene["finalVideoPrompt"] = self.production_orchestrator.compile_scene_prompt(plan, scene)
        scene["finalVideoPromptStale"] = False
        scene["promptQuality"] = self.production_orchestrator.lint_scene_prompt(scene)
        project.creative_plan = plan
        return self.storage.save_project(project)

    def update_keyframe_prompt_slot(
        self,
        project_id: str,
        scene_index: int,
        slot_id: str,
        payload: UpdateKeyframePromptSlotRequest,
    ) -> Project:
        project = self.storage.get_project(project_id)
        plan = self._require_plan(project)
        scene = self._find_scene(plan.scenes, scene_index)
        slot = self._find_keyframe_slot(scene, slot_id)
        values = payload.model_dump(exclude_unset=True)
        for key, value in values.items():
            if value is not None:
                slot[key] = value

        # Re-run prompt cleanup and product-reference routing after an edited
        # source prompt is saved. This keeps compiled UI instructions out of
        # storage and prevents stale product references from surviving edits.
        plan = CreativePlan.model_validate(plan.model_dump(mode="python"))
        scene = self._find_scene(plan.scenes, scene_index)
        slot = self._find_keyframe_slot(scene, slot_id)
        slot["stale"] = True
        scene["finalVideoPromptStale"] = True
        self.production_orchestrator.refresh_scene(plan, scene, compile_prompt=False)
        project.creative_plan = plan
        return self.storage.save_project(project)

    def select_keyframe_candidate(
        self,
        project_id: str,
        scene_index: int,
        slot_id: str,
        payload: SelectKeyframeCandidateRequest,
    ) -> Project:
        project = self.storage.get_project(project_id)
        plan = self._require_plan(project)
        scene = self._find_scene(plan.scenes, scene_index)
        slot = self._find_keyframe_slot(scene, slot_id)
        image_url = self._resolve_candidate_url(project, payload)
        if not image_url:
            raise ValueError("Provide imageUrl, fileId, or candidateId to select a keyframe candidate.")
        candidates = slot.setdefault("candidates", [])
        selected = None
        for candidate in candidates:
            if not isinstance(candidate, dict):
                continue
            if payload.candidateId and candidate.get("id") == payload.candidateId:
                selected = candidate
                break
            if candidate.get("imageUrl") == image_url:
                selected = candidate
                break
        if selected is None:
            selected = {
                "id": f"candidate_{len(candidates) + 1}",
                "imageUrl": image_url,
                "mimeType": None,
                "warning": None,
            }
            candidates.append(selected)
        slot["selectedCandidateId"] = selected["id"]
        slot["selectedImageUrl"] = selected["imageUrl"]
        slot["stale"] = False
        scene["finalVideoPromptStale"] = True
        scene["status"] = "KEYFRAME_READY"
        self.production_orchestrator.refresh_scene(plan, scene, compile_prompt=True)
        project.creative_plan = plan
        return self.storage.save_project(project)

    def generate_reference_asset_image(
        self,
        project_id: str,
        asset_type: str,
        *,
        model_id: str,
        progress_callback: ImageProgressCallback | None = None,
    ) -> Project:
        self._report_image_progress(progress_callback, 8, "Loading project")
        project = self.storage.get_project(project_id)
        plan = self._require_plan(project)
        normalized_type = asset_type.lower().strip()
        if normalized_type not in {"character", "location"}:
            raise ValueError("asset_type must be character or location.")
        asset = plan.primaryCharacter if normalized_type == "character" else plan.primaryLocation
        prompt = self._build_reference_asset_prompt(normalized_type, asset)
        selected_model = self.image_provider.resolve_model_id(model_id)
        generated = self.image_provider.generate_image(
            prompt=prompt,
            aspect_ratio="9:16",
            model_id=selected_model,
            reference_images=self._build_reference_asset_image_references(project, normalized_type, asset),
            progress_callback=progress_callback,
        )

        self._report_image_progress(progress_callback, 94, "Saving generated image")

        def apply_result(latest_project: Project) -> Project:
            latest_plan = self._require_plan(latest_project)
            latest_asset = latest_plan.primaryCharacter if normalized_type == "character" else latest_plan.primaryLocation
            saved = self.file_storage.save_generated_file(
                latest_project.id,
                bucket=normalized_type,
                filename=f"{normalized_type}_reference.png",
                content=generated.content,
                content_type=generated.content_type,
            )
            self._replace_reference_asset_file(latest_project, latest_asset, saved)
            latest_project.uploaded_files.append(saved)
            latest_asset["imageUrl"] = saved.url
            latest_asset["status"] = "ready"
            latest_asset["uploadedFileId"] = saved.id
            latest_asset["candidateImages"] = [saved.url]
            latest_asset["generationModel"] = selected_model
            latest_project.creative_plan = latest_plan
            return latest_project

        project = self.storage.mutate_project(project_id, apply_result)
        self._report_image_progress(progress_callback, 98, "Updating project")
        return project

    def update_reference_asset(self, project_id: str, asset_type: str, payload: UpdateReferenceAssetRequest) -> Project:
        project = self.storage.get_project(project_id)
        plan = self._require_plan(project)
        normalized_type = asset_type.lower().strip()
        if normalized_type not in {"character", "location"}:
            raise ValueError("asset_type must be character or location.")

        asset = plan.primaryCharacter if normalized_type == "character" else plan.primaryLocation
        values = payload.model_dump(exclude_unset=True)
        for key, value in values.items():
            if isinstance(value, str):
                cleaned = value.strip()
                if cleaned:
                    asset[key] = cleaned
            elif value is not None:
                asset[key] = value

        project.creative_plan = plan
        return self.storage.save_project(project)

    def generate_keyframe_slot_image(
        self,
        project_id: str,
        scene_index: int,
        slot_id: str,
        *,
        model_id: str,
        progress_callback: ImageProgressCallback | None = None,
    ) -> Project:
        self._report_image_progress(progress_callback, 8, "Loading scene contract")
        project = self.storage.get_project(project_id)
        plan = self._require_plan(project)
        scene = self._find_scene(plan.scenes, scene_index)
        slot = self._find_keyframe_slot(scene, slot_id)
        source_prompt = str(slot.get("prompt") or "").strip()
        product_reference_ids = [
            str(reference_id)
            for reference_id in (slot.get("productReferenceIds") or [])
            if str(reference_id).strip()
        ][:1]
        prompt = self._build_keyframe_image_prompt(plan, scene, slot)
        reference_images = self._build_keyframe_image_references(project, plan, scene, slot)
        selected_model = self.image_provider.resolve_model_id(model_id)
        generated = self.image_provider.generate_image(
            prompt=prompt,
            aspect_ratio="9:16",
            model_id=selected_model,
            reference_images=reference_images,
            progress_callback=progress_callback,
        )

        self._report_image_progress(progress_callback, 94, "Saving keyframe image")

        def apply_result(latest_project: Project) -> Project:
            latest_plan = self._require_plan(latest_project)
            latest_scene = self._find_scene(latest_plan.scenes, scene_index)
            latest_slot = self._find_keyframe_slot(latest_scene, slot_id)
            # Treat prompt + routed product reference as one atomic generation
            # contract. Provider latency and model re-validation must not replace
            # the selected app screen after generation.
            latest_slot["prompt"] = source_prompt
            latest_slot["productReferenceIds"] = product_reference_ids
            output_filename = self._keyframe_output_filename(scene_index, latest_scene, latest_slot)
            saved = self.file_storage.save_generated_file(
                latest_project.id,
                bucket="keyframe",
                filename=output_filename,
                content=generated.content,
                content_type=generated.content_type,
            )
            self._replace_keyframe_slot_file(latest_project, latest_slot, saved)
            latest_project.uploaded_files.append(saved)
            candidate = {
                "id": "candidate_1",
                "imageUrl": saved.url,
                "mimeType": saved.content_type,
                "warning": generated.warning,
            }
            latest_slot["candidates"] = [candidate]
            latest_slot["selectedCandidateId"] = candidate["id"]
            latest_slot["selectedImageUrl"] = candidate["imageUrl"]
            latest_slot["uploadedFileId"] = saved.id
            latest_slot["generationModel"] = selected_model
            latest_slot["stale"] = False
            latest_scene["status"] = "KEYFRAME_READY"
            latest_scene["finalVideoPromptStale"] = True
            self.production_orchestrator.refresh_scene(latest_plan, latest_scene, compile_prompt=True)
            latest_project.creative_plan = latest_plan
            return latest_project

        project = self.storage.mutate_project(project_id, apply_result)
        self._report_image_progress(progress_callback, 98, "Updating project")
        return project

    def _report_image_progress(
        self,
        callback: ImageProgressCallback | None,
        progress: int,
        phase: str,
    ) -> None:
        if callback:
            callback(progress, phase)

    async def upload_keyframe_slot_image(
        self,
        project_id: str,
        scene_index: int,
        slot_id: str,
        file: UploadFile | None,
    ) -> Project:
        if file is None:
            raise ValueError("Select one keyframe image to upload.")
        project = self.storage.get_project(project_id)
        plan = self._require_plan(project)
        scene = self._find_scene(plan.scenes, scene_index)
        slot = self._find_keyframe_slot(scene, slot_id)
        output_filename = self._keyframe_output_filename(scene_index, scene, slot)
        saved = await self.file_storage.save_named_upload(project.id, file, output_filename)
        self._replace_keyframe_slot_file(project, slot, saved)
        project.uploaded_files.append(saved)
        candidate = {
            "id": "candidate_1",
            "imageUrl": saved.url,
            "mimeType": saved.content_type,
            "warning": None,
        }
        slot["candidates"] = [candidate]
        slot["selectedCandidateId"] = candidate["id"]
        slot["selectedImageUrl"] = candidate["imageUrl"]
        slot["uploadedFileId"] = saved.id
        slot["stale"] = False
        scene["status"] = "KEYFRAME_READY"
        scene["finalVideoPromptStale"] = True
        self.production_orchestrator.refresh_scene(plan, scene, compile_prompt=True)
        project.creative_plan = plan
        return self.storage.save_project(project)

    def generate_scene_video(self, project_id: str, scene_index: int, model_id: str | None = None) -> Project:
        project = self.storage.get_project(project_id)
        plan = self._require_plan(project)
        scene = self._find_scene(plan.scenes, scene_index)
        if not str(scene.get("finalVideoPrompt") or "").strip():
            raise ValueError("Final video prompt is required before video generation.")
        prompt_quality = self.production_orchestrator.lint_scene_prompt(scene)
        scene["promptQuality"] = prompt_quality
        if prompt_quality.get("hardFailures"):
            raise ValueError("Video prompt quality gate failed: " + " ".join(prompt_quality["hardFailures"]))
        if scene.get("videoUrl"):
            return project

        missing = [
            slot.get("label") or slot.get("id")
            for slot in scene.get("keyframePrompts") or []
            if isinstance(slot, dict) and not slot.get("selectedImageUrl")
        ]
        if missing:
            raise ValueError(f"Select keyframe references before video generation: {', '.join(str(item) for item in missing)}")

        previous_job_id = str(scene.get("videoJobId") or "").strip()
        references = self._build_scene_video_references(project, plan, scene)
        if not references:
            raise ValueError("Upload or generate at least one keyframe/reference image before video generation.")

        selected_model = str(scene.get("videoModel") or model_id or "").strip() if previous_job_id else model_id
        profile = self.video_provider.get_model_profile(
            model_id=selected_model or None,
            duration=str(scene.get("videoDuration") or scene.get("durationSec") or DEFAULT_SCENE_CLIP_SECONDS),
        )
        scene["status"] = "VIDEO_GENERATING"
        scene["videoError"] = None
        scene["videoProvider"] = "ShopAIKey"
        scene["videoModel"] = profile.model_id
        scene["videoRatio"] = profile.ratio
        scene["videoDuration"] = profile.duration
        scene["videoMode"] = profile.mode
        scene["videoResolution"] = profile.resolution
        if not previous_job_id:
            scene["videoProgress"] = 0
        project.creative_plan = plan
        self.storage.save_project(project)

        try:
            if previous_job_id:
                uploaded_references = [
                    self._video_reference_upload_from_dict(item)
                    for item in scene.get("videoReferenceUploads") or []
                    if isinstance(item, dict)
                ]
                result = self.video_provider.poll_video(
                    project_id=project.id,
                    job_id=previous_job_id,
                    references=uploaded_references,
                    duration=str(scene.get("videoDuration") or scene.get("durationSec") or DEFAULT_SCENE_CLIP_SECONDS),
                    model_id=profile.model_id,
                )
            else:
                result = self.video_provider.generate_video(
                    project_id=project.id,
                    scene_index=scene_index,
                    prompt=str(scene.get("finalVideoPrompt") or ""),
                    references=references,
                    duration=str(scene.get("durationSec") or DEFAULT_SCENE_CLIP_SECONDS),
                    model_id=profile.model_id,
                )
        except VideoProviderError as exc:
            scene["status"] = "FAILED"
            scene["videoError"] = str(exc)
            if isinstance(exc, VideoTaskFailedError):
                scene["videoJobId"] = None
                scene["videoStatusPayload"] = None
                scene["videoReferenceUploads"] = []
            project.creative_plan = plan
            self.storage.save_project(project)
            raise

        self._apply_generated_video_result(scene, result)
        project.creative_plan = plan
        return self.storage.save_project(project)

    def poll_scene_video(self, project_id: str, scene_index: int) -> Project:
        project = self.storage.get_project(project_id)
        plan = self._require_plan(project)
        scene = self._find_scene(plan.scenes, scene_index)
        if scene.get("videoUrl"):
            return project
        if not str(scene.get("videoJobId") or "").strip():
            raise ValueError("Generate the scene video before polling its status.")
        return self.generate_scene_video(project_id, scene_index, str(scene.get("videoModel") or "") or None)

    async def upload_scene_video(self, project_id: str, scene_index: int, file: UploadFile | None) -> Project:
        if file is None:
            raise ValueError("Select one video file to upload.")
        project = self.storage.get_project(project_id)
        plan = self._require_plan(project)
        scene = self._find_scene(plan.scenes, scene_index)
        output_filename = self._scene_clip_output_filename(scene_index, scene)
        saved = await self.file_storage.save_named_upload(project.id, file, output_filename)
        self._replace_scene_video_file(project, scene, saved)
        project.uploaded_files.append(saved)
        scene["videoUrl"] = saved.url
        scene["uploadedVideoFileId"] = saved.id
        scene["status"] = "VIDEO_READY"
        scene["videoError"] = None
        scene["videoProgress"] = 100
        project.creative_plan = plan
        return self.storage.save_project(project)

    def review_scene_take(self, project_id: str, scene_index: int, payload: ReviewSceneTakeRequest) -> Project:
        project = self.storage.get_project(project_id)
        plan = self._require_plan(project)
        scene = self._find_scene(plan.scenes, scene_index)
        if not scene.get("videoUrl"):
            raise ValueError("Generate or upload the scene clip before reviewing the take.")
        self.production_orchestrator.review_take(plan, scene, payload.model_dump(mode="json"))
        project.creative_plan = plan
        return self.storage.save_project(project)

    def delete_project(self, project_id: str) -> None:
        self.storage.delete_project(project_id)

    def _reset_plan_generated_assets(self, project: Project) -> bool:
        if project.creative_plan is None:
            return False

        product_reference_ids = {
            str(reference.get("id"))
            for reference in project.creative_plan.productReferences
            if isinstance(reference, dict) and reference.get("id")
        }
        if not product_reference_ids:
            return False

        kept_files = []
        removed_files = []
        for uploaded_file in project.uploaded_files:
            if uploaded_file.id in product_reference_ids:
                kept_files.append(uploaded_file)
            else:
                removed_files.append(uploaded_file)

        if removed_files:
            self.file_storage.delete_uploaded_files(removed_files)
            project.uploaded_files = kept_files
            return True
        return False

    def _replace_reference_asset_file(self, project: Project, asset: dict, replacement: object) -> None:
        previous_file_id = str(asset.get("uploadedFileId") or "")
        previous_image_url = str(asset.get("imageUrl") or "")
        if not previous_file_id and not previous_image_url:
            return

        removed_files = []
        kept_files = []
        for uploaded_file in project.uploaded_files:
            should_remove = (
                bool(previous_file_id and uploaded_file.id == previous_file_id)
                or bool(previous_image_url and uploaded_file.url == previous_image_url)
            )
            if should_remove and uploaded_file.id != getattr(replacement, "id", None):
                removed_files.append(uploaded_file)
            else:
                kept_files.append(uploaded_file)

        if removed_files:
            self.file_storage.delete_uploaded_files(removed_files)
            project.uploaded_files = kept_files

    def _replace_keyframe_slot_file(self, project: Project, slot: dict, replacement: object) -> None:
        previous_file_id = str(slot.get("uploadedFileId") or "")
        previous_urls = {
            str(slot.get("selectedImageUrl") or ""),
            *[
                str(candidate.get("imageUrl") or "")
                for candidate in slot.get("candidates") or []
                if isinstance(candidate, dict)
            ],
        }
        previous_urls.discard("")
        if not previous_file_id and not previous_urls:
            return

        removed_files = []
        kept_files = []
        replacement_id = getattr(replacement, "id", None)
        for uploaded_file in project.uploaded_files:
            should_remove = (
                bool(previous_file_id and uploaded_file.id == previous_file_id)
                or uploaded_file.url in previous_urls
            )
            if should_remove and uploaded_file.id != replacement_id:
                removed_files.append(uploaded_file)
            else:
                kept_files.append(uploaded_file)

        if removed_files:
            self.file_storage.delete_uploaded_files(removed_files)
            project.uploaded_files = kept_files

    def _replace_scene_video_file(self, project: Project, scene: dict, replacement: object) -> None:
        previous_file_id = str(scene.get("uploadedVideoFileId") or "")
        previous_video_url = str(scene.get("videoUrl") or "")
        if not previous_file_id and not previous_video_url:
            return

        removed_files = []
        kept_files = []
        replacement_id = getattr(replacement, "id", None)
        for uploaded_file in project.uploaded_files:
            should_remove = (
                bool(previous_file_id and uploaded_file.id == previous_file_id)
                or bool(previous_video_url and uploaded_file.url == previous_video_url)
            )
            if should_remove and uploaded_file.id != replacement_id:
                removed_files.append(uploaded_file)
            else:
                kept_files.append(uploaded_file)

        if removed_files:
            self.file_storage.delete_uploaded_files(removed_files)
            project.uploaded_files = kept_files

    def _build_reference_asset_image_references(
        self,
        project: Project,
        asset_type: str,
        asset: dict,
    ) -> list[ImageReference]:
        existing_url = str(asset.get("imageUrl") or "").strip()
        if not existing_url:
            return []
        reference = self._image_reference_from_selector(
            project,
            label=f"{asset_type}_reference",
            role=f"existing {asset_type} identity and appearance",
            selector=existing_url,
        )
        return [reference] if reference else []

    def _build_keyframe_image_references(
        self,
        project: Project,
        plan: CreativePlan,
        scene: dict,
        slot: dict,
    ) -> list[ImageReference]:
        references: list[ImageReference] = []
        seen: set[str] = set()

        def add_reference(label: str, role: str, selector: object) -> None:
            reference = self._image_reference_from_selector(project, label, role, str(selector or ""))
            if reference is None:
                return
            identity = reference.file_path or reference.url or reference.id
            if identity in seen:
                return
            seen.add(identity)
            references.append(reference)

        relevant_product_refs = self._filter_product_references(
            plan.productReferences,
            slot.get("productReferenceIds"),
        )[:1]
        for product_ref in relevant_product_refs:
            label = str(
                product_ref.get("referenceLabel")
                or product_ref.get("sourceFileName")
                or product_ref.get("name")
                or "product_reference"
            )
            selector = product_ref.get("id") or product_ref.get("sourceFileName") or product_ref.get("name")
            add_reference(
                label,
                "pixel-locked product/app UI for this scene only; copy the visible reference unchanged into the product or phone screen",
                selector,
            )

        # Put the scene's hero product/UI reference first. Multimodal image
        # providers tend to preserve earlier image inputs more faithfully, and
        # the remaining references should only supply actor and environment.
        add_reference(
            "character_reference",
            "primary character identity, face, body, outfit, and age",
            plan.primaryCharacter.get("imageUrl"),
        )
        add_reference(
            "location_reference",
            "primary location layout, recurring props, lighting direction, and atmosphere",
            plan.primaryLocation.get("imageUrl"),
        )

        return references

    def _image_reference_from_selector(
        self,
        project: Project,
        label: str,
        role: str,
        selector: str,
    ) -> ImageReference | None:
        cleaned = selector.strip()
        if not cleaned:
            return None

        for uploaded_file in project.uploaded_files:
            if (
                cleaned == uploaded_file.id
                or cleaned == uploaded_file.url
                or cleaned == uploaded_file.file_name
                or cleaned.endswith(uploaded_file.url)
                or cleaned.endswith(uploaded_file.file_name)
            ):
                return ImageReference(
                    id=uploaded_file.id,
                    label=label,
                    role=role,
                    file_path=uploaded_file.path,
                    url=uploaded_file.url,
                    content_type=uploaded_file.content_type,
                )

        if cleaned.startswith("https://") or cleaned.startswith("http://") or cleaned.startswith("data:image/"):
            return ImageReference(
                id=cleaned,
                label=label,
                role=role,
                url=cleaned,
            )
        return None

    def _build_scene_video_references(self, project: Project, plan: CreativePlan, scene: dict) -> list[VideoReferenceInput]:
        references: list[VideoReferenceInput] = []
        seen: set[str] = set()

        def add_reference(label: str, role: str, url: object) -> None:
            reference = self._video_reference_from_url(project, label, role, str(url or ""))
            if reference is None:
                return
            key = reference.file_path or reference.url or reference.label
            if key in seen:
                return
            seen.add(key)
            references.append(reference)

        scene_index = int(scene.get("sceneIndex") or 0)
        for slot_index, slot in enumerate(scene.get("keyframePrompts") or [], start=1):
            if not isinstance(slot, dict):
                continue
            output_name = f"scene_{scene_index:02d}_keyframe_{slot_index:02d}.png"
            add_reference(output_name, "keyframe", slot.get("selectedImageUrl"))
            keyframe_count = len([reference for reference in references if reference.role == "keyframe"])
            if keyframe_count >= KEYFRAMES_PER_SCENE:
                break

        return references

    def _video_reference_from_url(self, project: Project, label: str, role: str, url: str) -> VideoReferenceInput | None:
        cleaned_url = url.strip()
        if not cleaned_url:
            return None

        for uploaded_file in project.uploaded_files:
            if (
                cleaned_url == uploaded_file.url
                or cleaned_url == uploaded_file.id
                or cleaned_url == uploaded_file.file_name
                or cleaned_url.endswith(uploaded_file.url)
                or cleaned_url.endswith(uploaded_file.file_name)
            ):
                return VideoReferenceInput(
                    label=label or uploaded_file.file_name,
                    role=role,
                    url=uploaded_file.url if uploaded_file.url.startswith(("http://", "https://")) else None,
                    file_path=uploaded_file.path,
                    content_type=uploaded_file.content_type,
                )

        if cleaned_url.startswith(("http://", "https://")):
            return VideoReferenceInput(label=label, role=role, url=cleaned_url)
        return None

    def _uploaded_file_for_product_reference(self, project: Project, reference: dict) -> object | None:
        reference_id = str(reference.get("id") or "")
        source_file_name = str(reference.get("sourceFileName") or "")
        reference_label = str(reference.get("referenceLabel") or "")
        for uploaded_file in project.uploaded_files:
            if uploaded_file.id == reference_id:
                return uploaded_file
            if source_file_name and uploaded_file.file_name == source_file_name:
                return uploaded_file
            if reference_label and reference_label in uploaded_file.file_name:
                return uploaded_file
        return None

    def _video_reference_upload_from_dict(self, value: dict) -> VideoReferenceUpload:
        return VideoReferenceUpload(
            label=str(value.get("label") or "reference"),
            role=str(value.get("role") or "reference"),
            url=str(value.get("url") or ""),
            source=str(value.get("source") or "") or None,
        )

    def _apply_generated_video_result(self, scene: dict, result: GeneratedVideo) -> None:
        scene["videoProvider"] = result.provider_name
        scene["videoModel"] = result.model_id
        scene["videoRatio"] = result.ratio
        scene["videoDuration"] = result.duration
        scene["videoMode"] = result.mode
        scene["videoResolution"] = result.resolution
        scene["videoProgress"] = result.progress
        scene["videoJobId"] = result.job_id
        scene["videoStatusPayload"] = result.raw_response
        scene["videoReferenceUploads"] = [
            {
                "label": reference.label,
                "role": reference.role,
                "url": reference.url,
                "source": reference.source,
            }
            for reference in result.references
        ]
        if result.video_url:
            scene["videoUrl"] = result.video_url
            scene["uploadedVideoFileId"] = None
            scene["status"] = "VIDEO_READY"
            scene["videoError"] = None
            return
        scene["status"] = result.status
        scene["videoError"] = result.message

    def _keyframe_output_filename(self, scene_index: int, scene: dict, slot: dict) -> str:
        slot_index = 1
        for index, candidate in enumerate(scene.get("keyframePrompts") or [], start=1):
            if candidate is slot:
                slot_index = index
                break
        return f"scene_{scene_index:02d}_keyframe_{slot_index:02d}.png"

    def _next_product_reference_index(self, project: Project) -> int:
        if project.creative_plan and project.creative_plan.productReferences:
            return len(project.creative_plan.productReferences) + 1
        existing_product_refs = [
            uploaded_file
            for uploaded_file in project.uploaded_files
            if uploaded_file.file_name.startswith("product_ref_")
        ]
        if existing_product_refs:
            return len(existing_product_refs) + 1
        return len(project.uploaded_files) + 1

    def _require_plan(self, project: Project) -> CreativePlan:
        if project.creative_plan is None:
            raise ValueError("Generate Plan Creation before using the production workflow.")
        return project.creative_plan

    def _llm_provider_for_project(self, project: Project) -> LLMProvider:
        return build_llm_provider()

    def _find_reference(self, references: list[dict], reference_id: str) -> dict:
        for reference in references:
            if reference.get("id") == reference_id or reference.get("name") == reference_id:
                return reference
        raise ValueError(f"Product reference '{reference_id}' was not found.")

    def _find_scene(self, scenes: list[dict], scene_index: int) -> dict:
        for scene in scenes:
            if int(scene.get("sceneIndex") or 0) == scene_index:
                return scene
        raise ValueError(f"Scene {scene_index} was not found.")

    def _find_keyframe_slot(self, scene: dict, slot_id: str) -> dict:
        slots = scene.setdefault("keyframePrompts", [])
        for slot in slots:
            if isinstance(slot, dict) and (slot.get("id") == slot_id or slot.get("label") == slot_id):
                return slot
        raise ValueError(f"Keyframe slot '{slot_id}' was not found.")

    def _normalize_voice_lines(self, value: list[dict]) -> list[dict]:
        normalized: list[dict] = []
        for item in value:
            line = str(item.get("line") or "").strip()
            if not line:
                continue
            normalized.append(
                {
                    "speaker": str(item.get("speaker") or "Primary actor").strip(),
                    "timing": str(item.get("timing") or "").strip(),
                    "actionState": str(item.get("actionState") or "").strip(),
                    "emotion": str(item.get("emotion") or "").strip(),
                    "delivery": str(item.get("delivery") or "").strip(),
                    "line": line,
                }
            )
        return normalized

    def _coerce_scene(self, data: dict, scene_index: int, previous: dict) -> dict:
        if "scene" in data and isinstance(data["scene"], dict):
            data = data["scene"]
        scene = dict(previous)
        scene.update(data)
        scene["sceneIndex"] = scene_index
        scene["durationSec"] = self._normalize_scene_duration(scene.get("durationSec"))
        scene["voiceLines"] = self._normalize_voice_lines(scene.get("voiceLines") or [])
        if not scene.get("keyframePrompts"):
            scene["keyframePrompts"] = previous.get("keyframePrompts") or []
        scene["keyframePrompts"] = self._normalize_keyframe_prompts(scene.get("keyframePrompts") or [])
        scene["finalVideoPrompt"] = self._clean_video_prompt(str(scene.get("finalVideoPrompt") or previous.get("finalVideoPrompt") or ""))
        scene["keyframePromptStale"] = True
        scene["finalVideoPromptStale"] = False
        return scene

    def _normalize_keyframe_prompts(self, slots: list) -> list:
        normalized = []
        for index, slot in enumerate(slots):
            if isinstance(slot, dict):
                next_slot = dict(slot)
                next_slot["id"] = "kf_main"
                next_slot["label"] = next_slot.get("label") or "Main keyframe"
                next_slot["timing"] = "0s"
                normalized.append(next_slot)
            if len(normalized) >= KEYFRAMES_PER_SCENE:
                break
        return normalized

    def _resolve_candidate_url(self, project: Project, payload: SelectKeyframeCandidateRequest) -> str | None:
        if payload.imageUrl:
            return payload.imageUrl
        if payload.fileId:
            for uploaded_file in project.uploaded_files:
                if uploaded_file.id == payload.fileId or uploaded_file.file_name == payload.fileId:
                    return uploaded_file.url
        if payload.candidateId:
            return None
        return None

    def _clean_video_prompt(self, prompt: str) -> str:
        import re

        cleaned = prompt.strip()
        cleaned = re.sub(
            r"^\s*Create\s+(?:exactly\s+)?(?:one\s+)?(?:an?\s+)?\d+\s*[- ]seconds?\s+(?:vertical\s+)?(?:\d+:\d+\s+)?(?:ad\s+)?(?:video|clip)\.?\s*",
            "",
            cleaned,
            flags=re.IGNORECASE,
        )
        cleaned = re.sub(r"\bCreate an? \d+\s*[- ]seconds? vertical video\.\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\bexact(?:ly)? \d+\s*[- ]seconds? duration,?\s*", "", cleaned, flags=re.IGNORECASE)
        return cleaned.strip() or prompt.strip()

    def _normalize_scene_duration(self, value: object) -> int:
        import re

        if isinstance(value, (int, float)):
            raw_duration = int(value)
        else:
            match = re.search(r"\d+", str(value or ""))
            raw_duration = int(match.group(0)) if match else DEFAULT_SCENE_CLIP_SECONDS
        return min(ALLOWED_SCENE_CLIP_SECONDS, key=lambda item: abs(item - raw_duration))

    def _scene_clip_output_filename(self, scene_index: int, scene: dict) -> str:
        duration = self._normalize_scene_duration(scene.get("durationSec"))
        return f"scene_{scene_index:02d}_clip_{duration}s.mp4"

    def _build_rewrite_scene_prompt(self, project: Project, plan: CreativePlan, scene: dict, instruction: str) -> str:
        import json

        return (
            "You are rewriting one scene in an existing short video ad plan.\n\n"
            "Return strict JSON for the updated scene only. No markdown.\n\n"
            f"Project context: {json.dumps(self._project_context(project, plan), ensure_ascii=False)}\n"
            f"Current scene JSON: {json.dumps(scene, ensure_ascii=False)}\n"
            f"User instruction: {instruction}\n\n"
            "Rules:\n"
            "1. Preserve sceneIndex and choose durationSec from 4, 6, 8, or 10 based on scene complexity.\n"
            "2. Keep the same product references, primary character, and primary location.\n"
            "3. Return all scene fields: title, visualAction, productMoment, characterAction, locationUse, camera, voiceLines, ambientAudio, onScreenText, timingBeats, keyframePrompts, finalVideoPrompt, negativeRules.\n"
            "4. Use structured voiceLines. Keep each voiceLines.line in the requested dialogue language, but keep all production planning fields in English unless the user explicitly asks the whole plan to use another language.\n"
            "5. Keep exactly 1 keyframePrompts item with id kf_main. Use productReferenceIds only for relevant product references. If the visual beat needs another keyframe, split it into another scene instead.\n"
            "6. finalVideoPrompt must be self-contained and include dialogue/audio, action, camera, product/character/location locks, reference image mapping, overlay intent, and negative rules.\n"
            "7. finalVideoPrompt must not mention duration, seconds, vertical format, portrait mode, or 9:16 because those are provider parameters.\n"
            "8. Preserve uploaded product/app/user references exactly. Do not redesign UI layout, text, colors, packaging, product shape, coin details, logo, or any user-provided visual reference.\n"
            "9. Spanish, Vietnamese, or other dialogue snippets must not change the language of title, goals, keyframe prompts, finalVideoPrompt, product locks, or production instructions.\n"
            "10. If quoted speech is needed inside a JSON string, use corner brackets instead of raw ASCII double quotes.\n"
        )

    def _build_regenerate_final_prompt(self, project: Project, plan: CreativePlan, scene: dict) -> str:
        import json

        selected_keyframes = [
            {
                "referenceIndex": index + 1,
                "id": slot.get("id"),
                "label": slot.get("label"),
                "timing": slot.get("timing"),
                "purpose": slot.get("purpose"),
                "prompt": slot.get("prompt"),
                "selectedImageUrl": slot.get("selectedImageUrl"),
            }
            for index, slot in enumerate((scene.get("keyframePrompts") or [])[:KEYFRAMES_PER_SCENE])
            if isinstance(slot, dict)
        ]
        return (
            "You are writing the final video prompt for one product/app ad scene.\n\n"
            'Return strict JSON only: {"finalVideoPrompt": "..."}\n\n'
            f"Project brief: {project.brief or project.product_description or project.product_name}\n"
            f"Product analysis JSON: {json.dumps(plan.productAnalysis, ensure_ascii=False)}\n"
            f"Product references JSON: {json.dumps(plan.productReferences, ensure_ascii=False)}\n"
            f"Primary character specs JSON: {json.dumps(plan.primaryCharacter, ensure_ascii=False)}\n"
            f"Primary location specs JSON: {json.dumps(plan.primaryLocation, ensure_ascii=False)}\n"
            f"Current scene JSON: {json.dumps(scene, ensure_ascii=False)}\n"
            f"Selected keyframe prompt slots JSON: {json.dumps(selected_keyframes, ensure_ascii=False)}\n"
            f"Current final video prompt: {scene.get('finalVideoPrompt') or ''}\n\n"
            "Rules:\n"
            "1. Output one self-contained finalVideoPrompt for a video model.\n"
            "2. The video model input will be one selected keyframe image plus this prompt.\n"
            "3. Treat the selected keyframe as the visual anchor and continue naturally from it; do not create a slideshow, montage, jump cut, or unrelated camera reset.\n"
            "4. Include this mapping in natural text: Reference image 1: main keyframe. Use it for the scene's visual anchor and product/actor/location lock.\n"
            "5. Include action chain, camera shot, movement, composition, product/app lock, primary character lock, location lock, native audio intent, overlay intent, and negative rules.\n"
            "6. Render every voiceLines item as direct dialogue with exact spoken text in ASCII quotes. Do not paraphrase spoken lines.\n"
            "7. If overlay text is empty, explicitly say: No overlay text. Do not request captions, subtitles, labels, slogans, lower-thirds, or random text.\n"
            "8. Do not mention duration, seconds, vertical format, portrait mode, or 9:16 inside finalVideoPrompt because those are provider parameters.\n"
            "9. Preserve uploaded product/app/user references exactly. Do not redesign UI layout, text, colors, packaging, product shape, coin details, logo, or any user-provided visual reference.\n"
            "10. Write finalVideoPrompt production instructions in English. Keep only direct dialogue/voiceover text in the requested dialogue language.\n"
            "11. Do not mention JSON, schemas, or internal field names inside finalVideoPrompt.\n"
        )

    def _project_context(self, project: Project, plan: CreativePlan) -> dict:
        return {
            "brief": project.brief,
            "productContext": project.product_description,
            "productAnalysis": plan.productAnalysis,
            "productReferences": plan.productReferences,
            "primaryCharacter": plan.primaryCharacter,
            "primaryLocation": plan.primaryLocation,
            "durationSecOptions": list(ALLOWED_SCENE_CLIP_SECONDS),
            "defaultDurationSec": DEFAULT_SCENE_CLIP_SECONDS,
            "aspectRatio": "9:16",
        }

    def _build_reference_asset_prompt(self, asset_type: str, asset: dict) -> str:
        if asset_type == "character":
            return (
                "Generate one clean primary character reference image for a short product/app ad.\n\n"
                f"Primary image prompt:\n{asset.get('imagePrompt') or ''}\n\n"
                f"Character description:\n{asset.get('description') or ''}\n\n"
                f"Identity lock:\n{asset.get('consistencyPrompt') or ''}\n\n"
                "Style: Modern commercial ad, natural lighting, clear face, neutral background, realistic proportions, no text, no watermark, no collage."
            )
        return (
            "Generate one clean location reference image for a short product/app ad.\n\n"
            f"Primary image prompt:\n{asset.get('imagePrompt') or ''}\n\n"
            f"Location description:\n{asset.get('description') or ''}\n\n"
            f"Location lock:\n{asset.get('consistencyPrompt') or ''}\n\n"
            "Style: Modern commercial ad environment, coherent lighting, clear usable space for actor and product/app, no text, no watermark, no collage. "
            "Create an attractive cinematic reference image, not a blueprint, survey photo, or empty symmetrical room."
        )

    def _build_keyframe_image_prompt(self, plan: CreativePlan, scene: dict, slot: dict) -> str:
        relevant_refs = self._filter_product_references(plan.productReferences, slot.get("productReferenceIds"))
        product_lock = "\n".join(
            str(ref.get("lockPrompt") or ref.get("visualDescription") or "").strip()
            for ref in relevant_refs
            if str(ref.get("lockPrompt") or ref.get("visualDescription") or "").strip()
        ) or str(plan.productAnalysis.get("productLockPrompt") or "Preserve the uploaded product/app exactly.")
        camera = scene.get("camera") or {}
        camera_context = "; ".join(
            str(item)
            for item in [camera.get("selected"), camera.get("shot"), camera.get("movement"), camera.get("composition")]
            if item
        )
        reference_contract = "\n".join(
            f"- @{ref.get('sourceFileName') or ref.get('name') or ref.get('referenceLabel')}: "
            f"transfer only {ref.get('lockPrompt') or ref.get('visualDescription') or 'the exact visible product appearance'}; "
            "ignore actor identity, location, camera, motion, and unrelated product states."
            for ref in relevant_refs
        ) or "- No uploaded product reference is required for this keyframe."
        direction = scene.get("direction") if isinstance(scene.get("direction"), dict) else {}
        compact_context = "; ".join(
            str(item).strip()
            for item in [
                scene.get("sceneGoal"),
                scene.get("visualAction"),
                scene.get("characterAction"),
                scene.get("productMoment"),
                direction.get("feltIntent"),
                direction.get("lighting"),
                direction.get("atmosphere"),
            ]
            if str(item or "").strip()
        )
        return (
            "Generate exactly one high-quality keyframe image for a short product/app ad.\n\n"
            f"Scene intention and visible state:\n{compact_context}\n\n"
            f"Keyframe prompt:\n{slot.get('prompt') or ''}\n\n"
            f"Reference transfer contract:\n{reference_contract}\n\n"
            f"Product lock:\n{product_lock}\n\n"
            f"Character lock:\n{plan.primaryCharacter.get('consistencyPrompt') or plan.primaryCharacter.get('description') or ''}\n\n"
            f"Location lock:\n{plan.primaryLocation.get('consistencyPrompt') or plan.primaryLocation.get('description') or ''}\n\n"
            f"Camera and composition:\n{camera_context}\n\n"
            "Rules: Spend this image on one visible beat and one readable hero subject. Use the relevant product, character, and location references for consistency when supported. "
            "Preserve uploaded product/app/user references exactly: do not redesign UI layout, text, colors, packaging, product shape, coin details, logo, or any visible product reference. "
            "Preserve face anatomy, hands, object ownership, wardrobe, product geometry, location layout, and motivated light direction. This is one keyframe candidate for one visual ingredient, not a collage and not a storyboard sheet. "
            "No subtitles, labels, numbers, watermarks, UI mock text, or extra symbols unless the product reference itself contains readable UI that must be shown."
        )

    def _filter_product_references(self, references: list[dict], reference_ids: object) -> list[dict]:
        if not isinstance(reference_ids, list):
            return references
        ordered_ids = [str(item) for item in reference_ids if str(item).strip()]
        if not ordered_ids:
            return []
        by_selector: dict[str, dict] = {}
        for reference in references:
            for selector in (reference.get("id"), reference.get("name"), reference.get("sourceFileName")):
                cleaned = str(selector or "").strip()
                if cleaned:
                    by_selector[cleaned] = reference

        ordered: list[dict] = []
        seen: set[int] = set()
        for reference_id in ordered_ids:
            reference = by_selector.get(reference_id)
            if reference is None or id(reference) in seen:
                continue
            seen.add(id(reference))
            ordered.append(reference)
        return ordered

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
