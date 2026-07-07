from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator, model_validator


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
    scenes: list[dict[str, Any]] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def migrate_legacy_storytelling_keys(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value

        value = dict(value)
        legacy_to_prompt = {
            "product_analysis": "productAnalysis",
            "product_references": "productReferences",
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
        return value

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
                    "durationSec": 4,
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


class HealthResponse(BaseModel):
    status: str
    service: str


class PlanCreationResult(BaseModel):
    vision_analysis: VisionAnalysis
    creative_plan: CreativePlan | None = None
