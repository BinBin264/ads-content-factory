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
    duration: str
    format: str
    hook: str
    script: str
    storyboard: list[StoryboardScene] = Field(default_factory=list)
    scene_prompts: list[str] = Field(default_factory=list)
    voiceover: str
    subtitles: list[str] = Field(default_factory=list)
    title: str
    caption: str
    cover_prompt: str
    video_status: Literal["draft", "rendering", "ready", "failed"] = "draft"
    mock_video_url: str | None = None
    export_9x16_url: str | None = None
    export_1x1_url: str | None = None


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
    product_brief: ProductBrief | None = None
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
