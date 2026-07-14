from datetime import datetime, timezone
import re
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator, model_validator


DEFAULT_SCENE_CLIP_SECONDS = 8
ALLOWED_SCENE_CLIP_SECONDS = (4, 6, 8, 10)
KEYFRAMES_PER_SCENE = 1


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def normalize_string_list(value: Any) -> list[str]:
    if value is None:
        return []

    values = value if isinstance(value, list) else [value]
    normalized: list[str] = []
    for item in values:
        if item is None:
            continue
        parts = str(item).replace("\n", ",").replace(";", ",").split(",")
        normalized.extend(part.strip() for part in parts if part.strip())
    return normalized


class UploadedFileInfo(BaseModel):
    id: str = Field(default_factory=lambda: new_id("file"))
    file_name: str
    content_type: str | None = None
    size_bytes: int
    path: str
    url: str


class VisionAnalysis(BaseModel):
    detected_objects: list[str] = Field(default_factory=list)
    detected_product_type: str = "general"
    detected_visual_style: str = "natural UGC"
    detected_brand_colors: list[str] = Field(default_factory=list)
    detected_ui_elements: list[str] = Field(default_factory=list)
    detected_text: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.5, ge=0, le=1)
    notes: list[str] = Field(default_factory=list)


class NormalizedBrief(BaseModel):
    product_name: str
    category: str
    product_type: str
    short_description: str
    target_audience: list[str] = Field(default_factory=list)
    main_problem: str
    main_benefit: str
    emotional_triggers: list[str] = Field(default_factory=list)
    functional_benefits: list[str] = Field(default_factory=list)
    proof_elements: list[str] = Field(default_factory=list)
    safe_claims: list[str] = Field(default_factory=list)
    claims_to_avoid: list[str] = Field(default_factory=list)
    recommended_visual_style: str
    recommended_ad_formats: list[str] = Field(default_factory=list)

    @field_validator("target_audience", mode="before")
    @classmethod
    def normalize_target_audience(cls, value: Any) -> list[str]:
        return normalize_string_list(value)


class CreativePlan(BaseModel):
    productAnalysis: dict[str, Any] = Field(default_factory=dict)
    productReferences: list[dict[str, Any]] = Field(default_factory=list)
    primaryCharacter: dict[str, Any] = Field(default_factory=dict)
    primaryLocation: dict[str, Any] = Field(default_factory=dict)
    scenes: list[dict[str, Any]] = Field(default_factory=list)
    storySpine: dict[str, Any] = Field(default_factory=dict)
    worldBible: dict[str, Any] = Field(default_factory=dict)
    surfaceProfile: dict[str, Any] = Field(default_factory=dict)
    safetyPlan: dict[str, Any] = Field(default_factory=dict)
    qualityStrategy: dict[str, Any] = Field(default_factory=dict)
    sequenceState: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def migrate_legacy_storytelling_keys(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value

        value = dict(value)
        legacy_to_prompt = {
            "product_analysis": "productAnalysis",
            "product_references": "productReferences",
            "primary_character": "primaryCharacter",
            "primary_location": "primaryLocation",
        }
        for legacy_key, prompt_key in legacy_to_prompt.items():
            if prompt_key not in value and legacy_key in value:
                value[prompt_key] = value[legacy_key]
        if not value.get("productAnalysis"):
            product_truth = str(value.get("product_truth") or value.get("main_message") or "").strip()
            forbidden_claims = normalize_string_list(value.get("forbidden_claims"))
            value["productAnalysis"] = {
                "productType": "not specified",
                "visibleElements": [],
                "coreBenefit": product_truth,
                "brandOrVisualCues": [],
                "doNotAssume": forbidden_claims,
                "productLockPrompt": str(value.get("visual_style") or "").strip(),
            }
        if not value.get("scenes"):
            value["scenes"] = cls._legacy_scenes_from_fields(value)
        if not value.get("primaryCharacter"):
            value["primaryCharacter"] = {
                "name": "Primary actor",
                "description": "Single consistent actor for this ad.",
                "imagePrompt": "Generate one realistic commercial actor reference image for this ad.",
                "consistencyPrompt": "Preserve the same actor identity, face, outfit, body type, and style across all keyframes.",
            }
        if not value.get("primaryLocation"):
            value["primaryLocation"] = {
                "name": "Primary setting",
                "description": "Consistent commercial filming location for this ad.",
                "imagePrompt": "Generate one realistic commercial location reference image for this ad.",
                "consistencyPrompt": "Preserve the same location, lighting, layout, and recurring prop relationships across all keyframes.",
            }
        if isinstance(value.get("scenes"), list):
            value["scenes"] = cls._normalize_keyframe_scenes(value["scenes"])
            value["scenes"] = cls._normalize_product_reference_usage(value["scenes"], value.get("productReferences") or [])
        return value

    @staticmethod
    def _normalize_keyframe_scenes(scenes: list[Any]) -> list[Any]:
        normalized: list[Any] = []
        for scene in scenes:
            if not isinstance(scene, dict):
                normalized.append(scene)
                continue
            next_scene = dict(scene)
            duration_seconds = CreativePlan._normalize_scene_duration(next_scene.get("durationSec"))
            next_scene["durationSec"] = duration_seconds
            final_prompt = str(next_scene.get("finalVideoPrompt") or "").strip()
            if final_prompt:
                next_scene["finalVideoPrompt"] = CreativePlan._clean_scene_video_prompt(final_prompt)
            voice_lines = next_scene.get("voiceLines")
            if isinstance(voice_lines, list):
                next_voice_lines = []
                for item in voice_lines:
                    if isinstance(item, dict):
                        next_item = dict(item)
                        if str(next_item.get("timing") or "").strip():
                            next_item["timing"] = f"0-{duration_seconds}s"
                        next_voice_lines.append(next_item)
                    else:
                        next_voice_lines.append(item)
                next_scene["voiceLines"] = next_voice_lines
            slots = next_scene.get("keyframePrompts")
            if isinstance(slots, list) and slots:
                next_slots = []
                for slot_index, slot in enumerate([slot for slot in slots if isinstance(slot, dict)][:KEYFRAMES_PER_SCENE]):
                    next_slot = dict(slot)
                    next_slot["id"] = "kf_main"
                    next_slot["label"] = next_slot.get("label") or "Main keyframe"
                    next_slot["timing"] = "0s"
                    next_slot["prompt"] = CreativePlan._clean_keyframe_source_prompt(next_slot.get("prompt"))
                    next_slots.append(next_slot)
                next_scene["keyframePrompts"] = next_slots
            normalized.append(next_scene)
        return normalized

    @staticmethod
    def _clean_keyframe_source_prompt(value: Any) -> str:
        reference_header = "Reference images to attach / mention in Flow:"
        source = str(value or "").strip()
        while source.startswith(reference_header):
            boundary = source.find("\n\n")
            if boundary < 0:
                return ""
            source = source[boundary + 2 :].lstrip()

        markers = ("\n\nAction:", "\n\nProduct moment:", "\n\nCamera:", "\n\nPreservation rule:")
        marker_indexes = [index for marker in markers if (index := source.find(marker)) >= 0]
        if marker_indexes:
            source = source[: min(marker_indexes)]
        return source.strip()

    @staticmethod
    def _normalize_product_reference_usage(scenes: list[Any], product_references: list[Any]) -> list[Any]:
        references = [reference for reference in product_references if isinstance(reference, dict)]
        reference_by_id = {str(reference.get("id") or ""): reference for reference in references}
        normalized: list[Any] = []
        for scene in scenes:
            if not isinstance(scene, dict):
                normalized.append(scene)
                continue
            next_scene = dict(scene)
            slots = next_scene.get("keyframePrompts")
            if isinstance(slots, list):
                next_slots = []
                for slot in slots:
                    if not isinstance(slot, dict):
                        next_slots.append(slot)
                        continue
                    next_slot = dict(slot)
                    next_slot["productReferenceIds"] = CreativePlan._select_product_reference_ids(next_scene, next_slot, reference_by_id)
                    next_slots.append(next_slot)
                next_scene["keyframePrompts"] = next_slots
            normalized.append(next_scene)
        return normalized

    @staticmethod
    def _select_product_reference_ids(scene: dict[str, Any], slot: dict[str, Any], reference_by_id: dict[str, dict[str, Any]]) -> list[str]:
        raw_ids = slot.get("productReferenceIds")
        searchable = " ".join(
            str(value or "")
            for value in [
                slot.get("prompt"),
                slot.get("purpose"),
                scene.get("title"),
                scene.get("visualAction"),
                scene.get("productMoment"),
                scene.get("characterAction"),
            ]
        ).lower()
        if CreativePlan._blocks_product_reference(searchable):
            return []

        candidate_ids = (
            [str(item or "").strip() for item in raw_ids if str(item or "").strip() in reference_by_id]
            if isinstance(raw_ids, list)
            else []
        )
        explicit_mentions: list[tuple[int, str]] = []
        for reference_id, reference in reference_by_id.items():
            aliases = [
                reference.get("name"),
                reference.get("sourceFileName"),
                reference.get("referenceLabel"),
            ]
            positions = [
                searchable.find(cleaned_alias)
                for alias in aliases
                if (cleaned_alias := str(alias or "").strip().lower()) and cleaned_alias in searchable
            ]
            if positions:
                explicit_mentions.append((min(positions), reference_id))
        if explicit_mentions:
            # A human-readable @filename in the keyframe source is the routing
            # contract. Do not let broader scene words such as "result" or
            # "scan" replace that exact reference on a later validation pass.
            return [min(explicit_mentions, key=lambda item: item[0])[1]]
        if not CreativePlan._needs_product_reference(searchable):
            return []

        priority_groups = [
            (("detail", "result", "value", "price", "rarity", "reference price", "price range"), ("detail", "result", "value", "price", "rarity", "coin_detail")),
            (("scan", "scanning", "capture button", "identify", "camera interface", "scan interface"), ("scan", "camera", "capture", "scan interface")),
            (("home screen", "start screen", "app home", "main screen"), ("home", "start")),
        ]
        for scene_keywords, reference_keywords in priority_groups:
            if not CreativePlan._contains_reference_keyword(searchable, scene_keywords):
                continue
            ordered_reference_ids = candidate_ids + [reference_id for reference_id in reference_by_id if reference_id not in candidate_ids]
            for candidate_id in ordered_reference_ids:
                reference = reference_by_id[candidate_id]
                reference_text = " ".join(
                    str(reference.get(key) or "")
                    for key in ("name", "sourceFileName", "referenceLabel", "visualDescription", "useWhen", "kind")
                ).lower()
                if CreativePlan._contains_reference_keyword(reference_text, reference_keywords):
                    return [candidate_id]
        return [candidate_ids[0]] if candidate_ids else []

    @staticmethod
    def _blocks_product_reference(text: str) -> bool:
        return any(
            phrase in text
            for phrase in (
                "no app visible",
                "no app is visible",
                "no app visible yet",
                "not showing the app yet",
                "phone is visible but kept hidden",
                "no product visible",
                "no ui visible",
                "no screen visible",
                "phone is lowered slightly, out of focus",
                "phone is now slightly out of focus",
                "out of focus below frame",
                "focus on character and cta",
                "focus on the physical coin",
            )
        )

    @staticmethod
    def _needs_product_reference(text: str) -> bool:
        return CreativePlan._contains_reference_keyword(
            text,
            (
                "phone screen",
                "smartphone screen",
                "app screen",
                "home screen",
                "app home",
                "main screen",
                "mobile app screen",
                "ui",
                "interface",
                "scan",
                "scanning",
                "capture button",
                "identify",
                "result",
                "detail",
                "reference price",
                "price range",
                "value range",
                "logo",
                "packaging",
                "package",
                "bottle",
                "jar",
                "tube",
                "box",
                "label",
            ),
        )

    @staticmethod
    def _contains_reference_keyword(text: str, keywords: tuple[str, ...]) -> bool:
        for keyword in keywords:
            normalized_keyword = keyword.lower()
            if " " in normalized_keyword or "_" in normalized_keyword:
                if normalized_keyword in text:
                    return True
                continue
            if re.search(rf"(?<![a-z0-9]){re.escape(normalized_keyword)}(?![a-z0-9])", text):
                return True
        return False

    @staticmethod
    def _normalize_scene_duration(value: Any) -> int:
        if isinstance(value, (int, float)):
            raw_duration = int(value)
        else:
            match = re.search(r"\d+", str(value or ""))
            raw_duration = int(match.group(0)) if match else DEFAULT_SCENE_CLIP_SECONDS
        return min(ALLOWED_SCENE_CLIP_SECONDS, key=lambda item: abs(item - raw_duration))

    @staticmethod
    def _clean_scene_video_prompt(prompt: str) -> str:
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

    @staticmethod
    def _legacy_scenes_from_fields(value: dict[str, Any]) -> list[dict[str, Any]]:
        product_truth = str(value.get("product_truth") or value.get("main_message") or "").strip()
        main_message = str(value.get("main_message") or product_truth or "Plan Creation").strip()
        visual_style = str(value.get("visual_style") or "").strip()
        scenes: list[dict[str, Any]] = []
        for index in range(2):
            title = "Storytelling setup" if index == 0 else "Product result"
            summary = main_message or product_truth
            scenes.append(
                {
                    "sceneIndex": index + 1,
                    "narrativePurpose": "hook + product_app_introduction" if index == 0 else "result + CTA",
                    "title": title,
                    "durationSec": DEFAULT_SCENE_CLIP_SECONDS,
                    "sceneGoal": summary,
                    "visualAction": summary,
                    "productMoment": product_truth,
                    "characterAction": "Primary actor follows the planned story beat.",
                    "locationUse": visual_style,
                    "camera": {
                        "selected": "stable vertical UGC shot",
                        "shot": "medium shot",
                        "movement": "natural handheld movement",
                        "composition": "product and actor remain readable",
                        "alternatives": [],
                    },
                    "voiceLines": [],
                    "ambientAudio": "native video audio",
                    "onScreenText": str(value.get("cta") or ""),
                    "timingBeats": [],
                    "keyframePrompts": [],
                    "finalVideoPrompt": summary,
                    "negativeRules": normalize_string_list(value.get("forbidden_claims")),
                }
            )
        return scenes

    @property
    def product_truth(self) -> str:
        return str(self.productAnalysis.get("coreBenefit") or "").strip()

    @property
    def audience_pain(self) -> str:
        scene = self.scenes[0] if self.scenes else {}
        return str(scene.get("sceneGoal") or scene.get("narrativePurpose") or "").strip()

    @property
    def main_message(self) -> str:
        scene = self.scenes[0] if self.scenes else {}
        return str(scene.get("title") or self.product_truth).strip()

    @property
    def safe_claims(self) -> list[str]:
        return [self.product_truth] if self.product_truth else []

    @property
    def forbidden_claims(self) -> list[str]:
        return normalize_string_list(self.productAnalysis.get("doNotAssume"))

    @property
    def cta(self) -> str:
        if not self.scenes:
            return "Learn more"
        final_scene = self.scenes[-1]
        text = str(final_scene.get("onScreenText") or final_scene.get("finalVideoPrompt") or "").strip()
        lowered = text.lower()
        if "download" in lowered:
            return "Download now"
        if "install" in lowered:
            return "Install now"
        if "buy" in lowered or "shop" in lowered:
            return "Shop now"
        return text[:80] or "Learn more"

    @property
    def visual_style(self) -> str:
        parts = [
            str(self.productAnalysis.get("productLockPrompt") or "").strip(),
        ]
        return "; ".join(part for part in parts if part) or "natural UGC"


class Project(BaseModel):
    id: str = Field(default_factory=lambda: new_id("project"))
    workflow_type: str = "video_ads"
    product_name: str
    product_category: str | None = None
    product_description: str | None = None
    brief: str | None = None
    audience: str | None = None
    goal: str = "app_install"
    platform: str = "tiktok"
    duration: str = "20s"
    tone: str = "UGC, natural, realistic"
    cta: str | None = None
    claims_to_avoid: list[str] = Field(default_factory=list)
    brand_colors: list[str] = Field(default_factory=list)
    uploaded_files: list[UploadedFileInfo] = Field(default_factory=list)
    vision_analysis: VisionAnalysis | None = None
    creative_plan: CreativePlan | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    @field_validator("claims_to_avoid", "brand_colors", mode="before")
    @classmethod
    def normalize_list_fields(cls, value: Any) -> list[str]:
        return normalize_string_list(value)

    @field_validator("workflow_type", mode="before")
    @classmethod
    def normalize_workflow_type(cls, value: Any) -> str:
        normalized = str(value or "video_ads").strip().lower().replace("-", "_")
        return normalized if normalized in {"video_ads", "content_creation"} else "video_ads"


class UpdateProductReferenceRequest(BaseModel):
    name: str | None = None
    kind: str | None = None
    visualDescription: str | None = None
    lockPrompt: str | None = None
    useWhen: str | None = None
    isPrimary: bool | None = None


class UpdateProjectRequest(BaseModel):
    product_description: str | None = None
    brief: str | None = None


class UpdateSceneRequest(BaseModel):
    title: str | None = None
    visualAction: str | None = None
    productMoment: str | None = None
    characterAction: str | None = None
    locationUse: str | None = None
    cameraShot: str | None = None
    cameraMovement: str | None = None
    composition: str | None = None
    voiceLine: str | None = None
    voiceLines: list[dict[str, Any]] | None = None
    ambientAudio: str | None = None
    onScreenText: str | None = None
    keyframePrompt: str | None = None


class RewriteSceneRequest(BaseModel):
    instruction: str


class UpdateSceneVideoPromptRequest(BaseModel):
    finalVideoPrompt: str


class GenerateSceneVideoRequest(BaseModel):
    model: Literal[
        "veo3.1-pro",
        "veo3.1-fast",
        "veo3.1-fast-components",
        "grok-video-3",
        "grok-video-3-10s",
    ] | None = None


ImageModelId = Literal[
    "nano-banana",
    "nano-banana-2",
    "nano-banana-pro",
    "gpt-image-1-mini",
    "gpt-image-1",
    "gpt-image-1.5",
    "gpt-image-2",
]


class GenerateImageRequest(BaseModel):
    model: ImageModelId


class ReviewSceneTakeRequest(BaseModel):
    verdict: str
    observed_start_state: dict[str, Any] = Field(default_factory=dict)
    observed_end_state: dict[str, Any] = Field(default_factory=dict)
    completed_beats: list[str] = Field(default_factory=list)
    continuity_breaks: list[str] = Field(default_factory=list)
    accepted_deviations: list[str] = Field(default_factory=list)
    changed_variable: str | None = None
    evidence: str | None = None
    observation_confidence: str = "medium"
    notes: str | None = None

    @field_validator("verdict")
    @classmethod
    def validate_verdict(cls, value: str) -> str:
        normalized = value.strip().lower().replace(" ", "_")
        allowed = {"keep", "fix_in_post", "edit", "reroll", "rewrite", "reject"}
        if normalized not in allowed:
            raise ValueError(f"verdict must be one of: {', '.join(sorted(allowed))}")
        return normalized

    @field_validator("observation_confidence")
    @classmethod
    def validate_observation_confidence(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"low", "medium", "high"}:
            raise ValueError("observation_confidence must be low, medium, or high")
        return normalized


class UpdateKeyframePromptSlotRequest(BaseModel):
    label: str | None = None
    timing: str | None = None
    purpose: str | None = None
    prompt: str | None = None
    productReferenceIds: list[str] | None = None


class ImageGenerationJob(BaseModel):
    id: str
    project_id: str
    job_type: str
    target_key: str
    scene_index: int | None = None
    slot_id: str | None = None
    asset_type: str | None = None
    model_id: str | None = None
    status: str = "queued"
    progress: int = 0
    phase: str = "Queued"
    attempt: int = 0
    max_attempts: int = 3
    error: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class UpdateReferenceAssetRequest(BaseModel):
    imagePrompt: str | None = None
    name: str | None = None
    description: str | None = None
    consistencyPrompt: str | None = None


class SelectKeyframeCandidateRequest(BaseModel):
    imageUrl: str | None = None
    fileId: str | None = None
    candidateId: str | None = None


class HealthResponse(BaseModel):
    status: str
    service: str


class PlanCreationResult(BaseModel):
    vision_analysis: VisionAnalysis
    creative_plan: CreativePlan | None = None
