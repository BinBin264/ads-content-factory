from fastapi import UploadFile

from app.models.schemas import (
    CreativePlan,
    Project,
    RewriteSceneRequest,
    SelectKeyframeCandidateRequest,
    UpdateKeyframePromptSlotRequest,
    UpdateProductReferenceRequest,
    UpdateReferenceAssetRequest,
    UpdateSceneRequest,
    UpdateSceneVideoPromptRequest,
)
from app.services.creative_plan_generator import CreativePlanGenerator, GeminiCreativePlanGenerator
from app.services.image_provider import OpenAICompatibleImageProvider
from app.services.llm_provider import LLMProvider, build_llm_provider
from app.services.storage_service import JsonProjectStorage, LocalFileStorage
from app.services.video_provider import (
    GeneratedVideo,
    GommoOmniVideoProvider,
    VideoProviderError,
    VideoReferenceInput,
    VideoReferenceUpload,
)


class ProjectService:
    def __init__(
        self,
        storage: JsonProjectStorage | None = None,
        file_storage: LocalFileStorage | None = None,
        creative_plan_generator: CreativePlanGenerator | None = None,
        llm_provider: LLMProvider | None = None,
        image_provider: OpenAICompatibleImageProvider | None = None,
        video_provider: GommoOmniVideoProvider | None = None,
    ) -> None:
        self.storage = storage or JsonProjectStorage()
        self.file_storage = file_storage or LocalFileStorage()
        self.creative_plan_generator = creative_plan_generator or GeminiCreativePlanGenerator()
        self.llm_provider = llm_provider or build_llm_provider()
        self.image_provider = image_provider or OpenAICompatibleImageProvider()
        self.video_provider = video_provider or GommoOmniVideoProvider()

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
        return self.storage.get_project(project_id)

    def generate_plan_creation(self, project_id: str) -> CreativePlan:
        project = self.storage.get_project(project_id)
        if self._reset_plan_generated_assets(project):
            project = self.storage.save_project(project)
        result = self.creative_plan_generator.create(project)
        if result.creative_plan is None:
            raise ValueError("Plan Creation generation did not return a creative_plan.")
        project.vision_analysis = result.vision_analysis
        project.creative_plan = result.creative_plan
        self.storage.save_project(project)
        return result.creative_plan

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

        project.creative_plan = plan
        return self.storage.save_project(project)

    def rewrite_scene(self, project_id: str, scene_index: int, payload: RewriteSceneRequest) -> Project:
        if not payload.instruction.strip():
            raise ValueError("Rewrite instruction is required.")
        project = self.storage.get_project(project_id)
        plan = self._require_plan(project)
        scene = self._find_scene(plan.scenes, scene_index)
        prompt = self._build_rewrite_scene_prompt(project, plan, scene, payload.instruction)
        rewritten = self.llm_provider.generate_json(prompt, temperature=0.35)
        updated = self._coerce_scene(rewritten, scene_index, scene)
        plan.scenes[plan.scenes.index(scene)] = updated
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
        project.creative_plan = plan
        return self.storage.save_project(project)

    def regenerate_scene_video_prompt(self, project_id: str, scene_index: int) -> Project:
        project = self.storage.get_project(project_id)
        plan = self._require_plan(project)
        scene = self._find_scene(plan.scenes, scene_index)
        prompt = self._build_regenerate_final_prompt(project, plan, scene)
        data = self.llm_provider.generate_json(prompt, temperature=0.25)
        final_prompt = str(data.get("finalVideoPrompt") or "").strip()
        if not final_prompt:
            raise ValueError("Gemini did not return finalVideoPrompt.")
        scene["finalVideoPrompt"] = self._force_four_second_prompt(final_prompt)
        scene["finalVideoPromptStale"] = False
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
        slot["stale"] = True
        scene["finalVideoPromptStale"] = True
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
        project.creative_plan = plan
        return self.storage.save_project(project)

    def generate_reference_asset_image(self, project_id: str, asset_type: str) -> Project:
        project = self.storage.get_project(project_id)
        plan = self._require_plan(project)
        normalized_type = asset_type.lower().strip()
        if normalized_type not in {"character", "location"}:
            raise ValueError("asset_type must be character or location.")
        asset = plan.primaryCharacter if normalized_type == "character" else plan.primaryLocation
        prompt = self._build_reference_asset_prompt(normalized_type, asset)
        generated = self.image_provider.generate_image(prompt=prompt, aspect_ratio="9:16")
        saved = self.file_storage.save_generated_file(
            project.id,
            bucket=normalized_type,
            filename=f"{normalized_type}_reference.png",
            content=generated.content,
            content_type=generated.content_type,
        )
        self._replace_reference_asset_file(project, asset, saved)
        project.uploaded_files.append(saved)
        asset["imageUrl"] = saved.url
        asset["status"] = "ready"
        asset["uploadedFileId"] = saved.id
        asset["candidateImages"] = [saved.url]
        project.creative_plan = plan
        return self.storage.save_project(project)

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

    def generate_keyframe_slot_image(self, project_id: str, scene_index: int, slot_id: str) -> Project:
        project = self.storage.get_project(project_id)
        plan = self._require_plan(project)
        scene = self._find_scene(plan.scenes, scene_index)
        slot = self._find_keyframe_slot(scene, slot_id)
        prompt = self._build_keyframe_image_prompt(plan, scene, slot)
        generated = self.image_provider.generate_image(prompt=prompt, aspect_ratio="9:16")
        output_filename = self._keyframe_output_filename(scene_index, scene, slot)
        saved = self.file_storage.save_generated_file(
            project.id,
            bucket="keyframe",
            filename=output_filename,
            content=generated.content,
            content_type=generated.content_type,
        )
        self._replace_keyframe_slot_file(project, slot, saved)
        project.uploaded_files.append(saved)
        candidate = {
            "id": "candidate_1",
            "imageUrl": saved.url,
            "mimeType": saved.content_type,
            "warning": generated.warning,
        }
        slot["candidates"] = [candidate]
        slot["selectedCandidateId"] = candidate["id"]
        slot["selectedImageUrl"] = candidate["imageUrl"]
        slot["uploadedFileId"] = saved.id
        slot["stale"] = False
        scene["status"] = "KEYFRAME_READY"
        scene["finalVideoPromptStale"] = True
        project.creative_plan = plan
        return self.storage.save_project(project)

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
        project.creative_plan = plan
        return self.storage.save_project(project)

    def generate_scene_video(self, project_id: str, scene_index: int) -> Project:
        project = self.storage.get_project(project_id)
        plan = self._require_plan(project)
        scene = self._find_scene(plan.scenes, scene_index)
        if not str(scene.get("finalVideoPrompt") or "").strip():
            raise ValueError("Final video prompt is required before video generation.")
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

        scene["status"] = "VIDEO_GENERATING"
        scene["videoError"] = None
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
                )
            else:
                result = self.video_provider.generate_video(
                    project_id=project.id,
                    scene_index=scene_index,
                    prompt=str(scene.get("finalVideoPrompt") or ""),
                    references=references,
                )
        except VideoProviderError as exc:
            scene["status"] = "FAILED"
            scene["videoError"] = str(exc)
            project.creative_plan = plan
            self.storage.save_project(project)
            raise

        self._apply_generated_video_result(scene, result)
        project.creative_plan = plan
        return self.storage.save_project(project)

    async def upload_scene_video(self, project_id: str, scene_index: int, file: UploadFile | None) -> Project:
        if file is None:
            raise ValueError("Select one video file to upload.")
        project = self.storage.get_project(project_id)
        plan = self._require_plan(project)
        scene = self._find_scene(plan.scenes, scene_index)
        output_filename = f"scene_{scene_index:02d}_clip_4s.mp4"
        saved = await self.file_storage.save_named_upload(project.id, file, output_filename)
        self._replace_scene_video_file(project, scene, saved)
        project.uploaded_files.append(saved)
        scene["videoUrl"] = saved.url
        scene["uploadedVideoFileId"] = saved.id
        scene["status"] = "VIDEO_READY"
        scene["videoError"] = None
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
        scene["durationSec"] = 4
        scene["voiceLines"] = self._normalize_voice_lines(scene.get("voiceLines") or [])
        if not scene.get("keyframePrompts"):
            scene["keyframePrompts"] = previous.get("keyframePrompts") or []
        scene["finalVideoPrompt"] = self._force_four_second_prompt(str(scene.get("finalVideoPrompt") or previous.get("finalVideoPrompt") or ""))
        scene["keyframePromptStale"] = True
        scene["finalVideoPromptStale"] = False
        return scene

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

    def _force_four_second_prompt(self, prompt: str) -> str:
        import re

        prompt = re.sub(r"\b\d+\s*[- ]seconds?\b", "4-second", prompt.strip(), flags=re.IGNORECASE)
        if prompt and "4-second vertical video" not in prompt.lower():
            prompt = f"Create a 4-second vertical video. {prompt}"
        return prompt

    def _build_rewrite_scene_prompt(self, project: Project, plan: CreativePlan, scene: dict, instruction: str) -> str:
        import json

        return (
            "You are rewriting one 4-second scene in an existing short video ad plan.\n\n"
            "Return strict JSON for the updated scene only. No markdown.\n\n"
            f"Project context: {json.dumps(self._project_context(project, plan), ensure_ascii=False)}\n"
            f"Current scene JSON: {json.dumps(scene, ensure_ascii=False)}\n"
            f"User instruction: {instruction}\n\n"
            "Rules:\n"
            "1. Preserve sceneIndex and set durationSec to exactly 4.\n"
            "2. Keep the same product references, primary character, and primary location.\n"
            "3. Return all scene fields: title, visualAction, productMoment, characterAction, locationUse, camera, voiceLines, ambientAudio, onScreenText, timingBeats, keyframePrompts, finalVideoPrompt, negativeRules.\n"
            "4. Use structured voiceLines. Keep each voiceLines.line in the project voice language unless instructed otherwise.\n"
            "5. Keep 1 to 2 keyframePrompts. Use productReferenceIds only for relevant product references.\n"
            "6. finalVideoPrompt must be self-contained and include dialogue/audio, action, camera, 4-second duration, product/character/location locks, reference image mapping, overlay intent, and negative rules.\n"
            "7. If quoted speech is needed inside a JSON string, use corner brackets instead of raw ASCII double quotes.\n"
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
            for index, slot in enumerate(scene.get("keyframePrompts") or [])
            if isinstance(slot, dict)
        ]
        return (
            "You are writing the final video prompt for one 4-second scene in a product/app ad.\n\n"
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
            "2. The video model input will be selected keyframe images plus this prompt.\n"
            "3. Treat selected keyframes as ordered visual ingredients, not an automatic slideshow.\n"
            "4. Include this mapping in natural text: Reference image 1: slot label. Use it for slot purpose.\n"
            "5. Include action chain, camera shot, movement, composition, exact 4-second duration, product/app lock, primary character lock, location lock, native audio intent, overlay intent, and negative rules.\n"
            "6. Render every voiceLines item as direct dialogue with exact spoken text in ASCII quotes. Do not paraphrase spoken lines.\n"
            "7. If overlay text is empty, explicitly say: No overlay text. Do not request captions, subtitles, labels, slogans, lower-thirds, or random text.\n"
            "8. Do not mention JSON, schemas, or internal field names inside finalVideoPrompt.\n"
        )

    def _project_context(self, project: Project, plan: CreativePlan) -> dict:
        return {
            "brief": project.brief,
            "productContext": project.product_description,
            "productAnalysis": plan.productAnalysis,
            "productReferences": plan.productReferences,
            "primaryCharacter": plan.primaryCharacter,
            "primaryLocation": plan.primaryLocation,
            "durationSec": 4,
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
        import json

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
        return (
            "Generate exactly one high-quality keyframe image for a short product/app ad.\n\n"
            "Aspect ratio: 9:16\n\n"
            f"Keyframe slot label:\n{slot.get('label') or ''}\n\n"
            f"Keyframe slot timing:\n{slot.get('timing') or ''}\n\n"
            f"Keyframe slot purpose:\n{slot.get('purpose') or ''}\n\n"
            f"Scene context:\n{json.dumps(scene, ensure_ascii=False)}\n\n"
            f"Keyframe prompt:\n{slot.get('prompt') or ''}\n\n"
            f"Relevant product references:\n{json.dumps(relevant_refs, ensure_ascii=False)}\n\n"
            f"Product lock:\n{product_lock}\n\n"
            f"Character lock:\n{plan.primaryCharacter.get('consistencyPrompt') or plan.primaryCharacter.get('description') or ''}\n\n"
            f"Location lock:\n{plan.primaryLocation.get('consistencyPrompt') or plan.primaryLocation.get('description') or ''}\n\n"
            f"Camera and composition:\n{camera_context}\n\n"
            "Rules: Use the relevant product, character, and location references for consistency when supported. "
            "This is one keyframe candidate for one visual ingredient, not a collage and not a storyboard sheet. "
            "No subtitles, labels, numbers, watermarks, UI mock text, or extra symbols unless the product reference itself contains readable UI that must be shown."
        )

    def _filter_product_references(self, references: list[dict], reference_ids: object) -> list[dict]:
        if not isinstance(reference_ids, list):
            return references
        ids = {str(item) for item in reference_ids}
        if not ids:
            return []
        return [reference for reference in references if str(reference.get("id")) in ids or str(reference.get("name")) in ids]

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
