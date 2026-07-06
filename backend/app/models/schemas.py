from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


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


class Playbook(BaseModel):
    playbook_id: str
    name: str
    best_for: list[str] = Field(default_factory=list)
    structure: list[str] = Field(default_factory=list)
    recommended_angles: list[str] = Field(default_factory=list)
    scene_formula: list[str] = Field(default_factory=list)


class ProductIntelligenceBrief(BaseModel):
    detected_product: str
    product_category: str
    product_type: str
    core_use_case: str
    target_audience_segments: list[str] = Field(default_factory=list)
    primary_audience: str
    pain_points: list[str] = Field(default_factory=list)
    emotional_triggers: list[str] = Field(default_factory=list)
    functional_benefits: list[str] = Field(default_factory=list)
    proof_points: list[str] = Field(default_factory=list)
    demo_moments: list[str] = Field(default_factory=list)
    visual_assets_detected: list[str] = Field(default_factory=list)
    brand_style_notes: str
    safe_claims: list[str] = Field(default_factory=list)
    claims_to_avoid: list[str] = Field(default_factory=list)
    recommended_ad_playbooks: list[Playbook] = Field(default_factory=list)
    recommended_video_formats: list[str] = Field(default_factory=list)
    recommended_hooks: list[str] = Field(default_factory=list)
    recommended_cta: str
    confidence_score: float = Field(default=0.65, ge=0, le=1)


class ProductBrief(BaseModel):
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


class VariantDirection(BaseModel):
    id: str = Field(default_factory=lambda: new_id("direction"))
    name: str
    hypothesis: str
    creative_angle: str
    best_for_metric: str


class CreativePlan(BaseModel):
    product_truth: str
    audience_pain: str
    main_message: str
    safe_claims: list[str] = Field(default_factory=list)
    forbidden_claims: list[str] = Field(default_factory=list)
    cta: str
    visual_style: str
    variant_directions: list[VariantDirection] = Field(default_factory=list)


class CreativeAngle(BaseModel):
    id: str = Field(default_factory=lambda: new_id("angle"))
    name: str
    angle_type: str
    target_audience: str
    pain_point: str
    emotional_trigger: str
    hook: str
    product_role: str
    proof_demo_moment: str
    cta: str
    reason_why_it_can_work: str
    score: float = Field(ge=0, le=100)
    hypothesis: str | None = None
    best_for_metric: str | None = None


class StoryboardScene(BaseModel):
    scene_number: int
    duration_seconds: int
    objective: str
    visual_description: str
    camera_angle: str
    on_screen_text: str
    voiceover_line: str
    transition: str
    generation_prompt: str
    negative_prompt: str


class VariantTimelineScene(BaseModel):
    scene: int
    time: str
    objective: str
    visual: str
    voiceover: str
    on_screen_text: str
    camera: str
    transition: str
    video_prompt: str
    negative_prompt: str


class CharacterPlan(BaseModel):
    recommended_character_type: str
    reason: str
    gender: str
    age_range: str
    ethnicity_or_look: str
    face_details: str
    hair: str
    facial_hair: str
    body_type: str
    outfit: str
    setting: str
    props: list[str] = Field(default_factory=list)
    personality: list[str] = Field(default_factory=list)
    speaking_style: str
    visual_style: str
    role_in_ad: str
    consistency_locks: list[str] = Field(default_factory=list)
    negative_identity_changes: list[str] = Field(default_factory=list)


class CharacterBible(BaseModel):
    character_id: str = Field(default_factory=lambda: new_id("character"))
    display_name: str
    role: str
    gender: str
    age_range: str
    ethnicity_or_look: str
    face_details: str
    hair: str
    facial_hair: str
    body_type: str
    outfit: str
    props: list[str] = Field(default_factory=list)
    setting: str
    personality: list[str] = Field(default_factory=list)
    speaking_style: str
    visual_style: str
    consistency_locks: list[str] = Field(default_factory=list)
    negative_identity_changes: list[str] = Field(default_factory=list)
    base_prompt: str
    identity_lock_prompt: str


class CharacterReferencePrompt(BaseModel):
    reference_id: str
    purpose: str
    aspect_ratio: str
    prompt: str
    negative_prompt: str
    notes: str = ""


class UIOverlayItem(BaseModel):
    overlay_type: Literal[
        "app_screen",
        "app_screen_overlay",
        "text_overlay",
        "subtitle",
        "cta",
        "disclaimer",
        "logo",
        "price_label",
        "button",
        "highlight",
    ]
    text: str
    start_time: str
    end_time: str
    position: str
    style_notes: str
    safety_notes: str


class ProductionScene(BaseModel):
    scene_number: int
    duration_seconds: int
    creative_objective: str
    shot_type: str
    camera_angle: str
    generation_mode: Literal["text_to_image", "image_to_video", "reference_to_video", "overlay_only"]
    required_reference_assets: list[str] = Field(default_factory=list)
    visual_description: str
    action_description: str
    keyframe_prompt: str
    video_prompt: str
    motion_instruction: str
    consistency_instruction: str
    negative_prompt: str
    ui_overlay_plan: list[UIOverlayItem] = Field(default_factory=list)
    voiceover_line: str
    on_screen_text: str
    transition: str
    safety_notes: str


class EditPlan(BaseModel):
    total_duration: str
    pacing_notes: str
    music_direction: str
    subtitle_style: str
    cut_sequence: list[str] = Field(default_factory=list)
    export_ratios: list[str] = Field(default_factory=list)
    required_post_production_steps: list[str] = Field(default_factory=list)
    platform_notes: str


class VideoProductionPackage(BaseModel):
    variant_id: str
    creative_angle_id: str
    character_plan: CharacterPlan
    character_bible: CharacterBible
    character_reference_prompts: list[CharacterReferencePrompt] = Field(default_factory=list)
    production_scenes: list[ProductionScene] = Field(default_factory=list)
    edit_plan: EditPlan
    app_ui_overlay_notes: str
    asset_checklist: list[str] = Field(default_factory=list)
    compliance_notes: list[str] = Field(default_factory=list)
    render_sequence: list[str] = Field(default_factory=list)


PipelineAssetType = Literal["image", "video", "audio", "app_screenshot", "subtitle", "json", "zip"]
PipelineAssetSource = Literal["uploaded_by_user", "generated_by_provider", "project_upload", "exported"]
PipelineStage = Literal[
    "character_reference",
    "scene_keyframe",
    "video_clip",
    "app_ui_overlay",
    "voiceover",
    "subtitles",
    "assembly",
    "export",
]
PipelineToolType = Literal[
    "image_generation",
    "video_generation",
    "image_editing",
    "video_editing",
    "tts",
    "subtitle_generation",
    "final_assembly",
    "export",
]
PipelineExecutionMode = Literal["manual_or_provider", "provider_only", "manual_only"]
PipelineStepStatus = Literal["pending", "ready", "running", "completed", "failed", "skipped"]
PipelineStatus = Literal["draft", "in_progress", "completed", "failed"]


class PipelineAsset(BaseModel):
    asset_id: str = Field(default_factory=lambda: new_id("asset"))
    asset_key: str
    asset_type: PipelineAssetType
    label: str
    url: str | None = None
    path: str | None = None
    source: PipelineAssetSource
    source_step_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class PipelineRequiredInput(BaseModel):
    asset_key: str
    asset_type: str
    label: str
    required: bool = True
    accepted_sources: list[str] = Field(default_factory=list)
    instructions: str


class PipelineExpectedOutput(BaseModel):
    asset_key: str
    asset_type: str
    label: str
    file_name_hint: str
    required_for_next_steps: list[str] = Field(default_factory=list)


class PipelineStep(BaseModel):
    step_id: str
    step_number: int
    stage: PipelineStage
    stage_label: str | None = None
    stage_purpose: str | None = None
    title: str
    goal: str
    tool_type: PipelineToolType
    execution_mode: PipelineExecutionMode = "manual_or_provider"
    provider_capability: str | None = None
    source_artifacts: list[str] = Field(default_factory=list)
    required_inputs: list[PipelineRequiredInput] = Field(default_factory=list)
    prompt_to_copy: str | None = None
    negative_prompt_to_copy: str | None = None
    motion_instruction: str | None = None
    consistency_instruction: str | None = None
    settings: dict[str, Any] = Field(default_factory=dict)
    expected_outputs: list[PipelineExpectedOutput] = Field(default_factory=list)
    review_focus: list[str] = Field(default_factory=list)
    success_criteria: list[str] = Field(default_factory=list)
    status: PipelineStepStatus = "pending"
    output_assets: list[PipelineAsset] = Field(default_factory=list)
    manual_instructions: list[str] = Field(default_factory=list)
    provider_options: list[dict[str, Any]] = Field(default_factory=list)
    provider_payload: dict[str, Any] = Field(default_factory=dict)
    error_message: str | None = None


class VariantGenerationPipeline(BaseModel):
    pipeline_id: str = Field(default_factory=lambda: new_id("pipeline"))
    variant_id: str
    pipeline_name: str = "ad_video_generation"
    pipeline_version: str = "1.0"
    objective: str = "Generate a linked manual-or-provider video production workflow."
    status: PipelineStatus = "draft"
    source_artifacts: list[dict[str, Any]] = Field(default_factory=list)
    stage_contracts: list[dict[str, Any]] = Field(default_factory=list)
    provider_contracts: list[dict[str, Any]] = Field(default_factory=list)
    assets: list[PipelineAsset] = Field(default_factory=list)
    steps: list[PipelineStep] = Field(default_factory=list)


class OptimizedVideoPrompt(BaseModel):
    video_prompt: str
    negative_prompt: str
    camera_instruction: str
    motion_instruction: str
    consistency_instruction: str
    duration_seconds: int
    aspect_ratio: str = "9:16"


class Variant(BaseModel):
    id: str = Field(default_factory=lambda: new_id("variant"))
    angle_id: str
    name: str
    hypothesis: str | None = None
    target_metric: str | None = None
    duration: str
    format: str
    hook: str
    script_summary: str | None = None
    timeline: list[VariantTimelineScene] = Field(default_factory=list)
    script: str
    storyboard: list[StoryboardScene] = Field(default_factory=list)
    scene_prompts: list[str] = Field(default_factory=list)
    voiceover: str
    subtitles: list[str] = Field(default_factory=list)
    title: str
    caption: str
    cover_prompt: str
    character_bible: dict[str, Any] | None = None
    visual_bible: dict[str, Any] | None = None
    asset_reference_map: dict[str, Any] | None = None
    production_package: VideoProductionPackage | None = None
    generation_pipeline: VariantGenerationPipeline | None = None
    selected_playbook: str | None = None
    angle_type: str | None = None
    video_status: Literal["draft", "package_exported", "rendering", "ready", "failed"] = "draft"
    video_url: str | None = None
    export_9x16_url: str | None = None
    export_1x1_url: str | None = None
    export_package_url: str | None = None


class Project(BaseModel):
    id: str = Field(default_factory=lambda: new_id("project"))
    product_name: str
    product_category: str | None = None
    product_description: str | None = None
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
    product_brief: ProductBrief | None = None
    product_intelligence: ProductIntelligenceBrief | None = None
    creative_plan: CreativePlan | None = None
    creative_angles: list[CreativeAngle] = Field(default_factory=list)
    variants: list[Variant] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    @field_validator("claims_to_avoid", "brand_colors", mode="before")
    @classmethod
    def normalize_list_fields(cls, value: Any) -> list[str]:
        return normalize_string_list(value)


class GenerateVariantsRequest(BaseModel):
    angle_ids: list[str] | None = None
    variant_count: int = Field(default=2, ge=1, le=5)


class HealthResponse(BaseModel):
    status: str
    service: str


class AnalyzeProjectResponse(BaseModel):
    product_intelligence: ProductIntelligenceBrief
    product_brief: ProductBrief
    vision_analysis: VisionAnalysis
    creative_plan: CreativePlan | None = None
