import json
from typing import Any

from app.models.schemas import (
    CreativeAngle,
    CreativePlan,
    Playbook,
    ProductBrief,
    ProductIntelligenceBrief,
    Project,
    VariantDirection,
    VisionAnalysis,
)
from app.services.llm_provider import LLMProvider, build_llm_provider
from app.services.playbook_engine import PlaybookEngine


class BriefNormalizer:
    def normalize(self, project: Project, vision: VisionAnalysis) -> ProductBrief:
        product_type = self._product_type(project, vision)
        description = project.product_description or f"{project.product_name} product brief."
        audience = self._string_list(project.audience) or ["target customers"]
        claims_to_avoid = project.claims_to_avoid
        visual_style = project.tone or vision.detected_visual_style or "natural UGC, realistic, mobile-first"
        if vision.detected_visual_style and vision.detected_visual_style not in visual_style:
            visual_style = f"{visual_style}; detected assets: {vision.detected_visual_style}"

        return ProductBrief(
            product_name=project.product_name,
            category=project.product_category or vision.detected_product_type or "general",
            product_type=product_type,
            short_description=description,
            target_audience=audience,
            main_problem="Audience needs a clear, believable reason to care now.",
            main_benefit=description,
            emotional_triggers=[],
            functional_benefits=[description],
            proof_elements=vision.detected_ui_elements + vision.detected_objects,
            safe_claims=[],
            claims_to_avoid=claims_to_avoid,
            recommended_visual_style=visual_style,
            recommended_ad_formats=[project.platform, project.duration],
        )

    def _product_type(self, project: Project, vision: VisionAnalysis) -> str:
        raw = f"{project.product_category or ''} {vision.detected_product_type}".lower().replace("-", "_").replace(" ", "_")
        if "app" in raw or "mobile" in raw or "software" in raw:
            return "mobile_app"
        if "skin" in raw or "beauty" in raw:
            return "skincare"
        if "food" in raw or "drink" in raw or "coffee" in raw or "fnb" in raw:
            return "fnb"
        if "education" in raw or "learning" in raw:
            return "education"
        if "ecommerce" in raw or "e_commerce" in raw or "shop" in raw:
            return "ecommerce"
        return vision.detected_product_type if vision.detected_product_type in {"mobile_app", "skincare", "fnb", "ecommerce", "education"} else "general"

    def _string_list(self, value: str | None) -> list[str]:
        if not value:
            return []
        return [item.strip() for item in value.replace("\n", ",").replace(";", ",").split(",") if item.strip()]


class CreativePlanService:
    RESPONSE_SCHEMA = {
        "type": "object",
        "properties": {
            "product_truth": {"type": "string"},
            "audience_pain": {"type": "string"},
            "main_message": {"type": "string"},
            "safe_claims": {"type": "array", "items": {"type": "string"}},
            "forbidden_claims": {"type": "array", "items": {"type": "string"}},
            "cta": {"type": "string"},
            "visual_style": {"type": "string"},
            "variant_directions": {
                "type": "array",
                "minItems": 2,
                "maxItems": 2,
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "hypothesis": {"type": "string"},
                        "creative_angle": {"type": "string"},
                        "best_for_metric": {"type": "string"},
                    },
                    "required": ["name", "hypothesis", "creative_angle", "best_for_metric"],
                },
            },
        },
        "required": [
            "product_truth",
            "audience_pain",
            "main_message",
            "safe_claims",
            "forbidden_claims",
            "cta",
            "visual_style",
            "variant_directions",
        ],
    }

    def __init__(
        self,
        llm_provider: LLMProvider | None = None,
        playbook_engine: PlaybookEngine | None = None,
    ) -> None:
        self.llm_provider = llm_provider or build_llm_provider()
        self.playbook_engine = playbook_engine or PlaybookEngine()

    def build(self, project: Project, brief: ProductBrief, vision: VisionAnalysis) -> CreativePlan:
        prompt = self._build_prompt(project, brief, vision)
        data = self.llm_provider.generate_json(prompt, temperature=0.35, response_schema=self.RESPONSE_SCHEMA)
        return CreativePlan.model_validate(self._coerce_plan(data, project, brief, vision))

    def to_product_brief(self, project: Project, brief: ProductBrief, plan: CreativePlan) -> ProductBrief:
        return brief.model_copy(
            update={
                "main_problem": plan.audience_pain,
                "main_benefit": plan.main_message,
                "functional_benefits": [plan.main_message, plan.product_truth],
                "proof_elements": plan.safe_claims,
                "safe_claims": plan.safe_claims,
                "claims_to_avoid": plan.forbidden_claims or project.claims_to_avoid,
                "recommended_visual_style": plan.visual_style,
            }
        )

    def to_product_intelligence(self, project: Project, brief: ProductBrief, plan: CreativePlan) -> ProductIntelligenceBrief:
        intelligence = ProductIntelligenceBrief(
            detected_product=project.product_name,
            product_category=brief.category,
            product_type=brief.product_type,
            core_use_case=plan.product_truth,
            target_audience_segments=brief.target_audience,
            primary_audience=", ".join(brief.target_audience) or project.audience or "target customers",
            pain_points=[plan.audience_pain],
            emotional_triggers=[plan.variant_directions[0].creative_angle] if plan.variant_directions else [],
            functional_benefits=[plan.main_message, plan.product_truth],
            proof_points=plan.safe_claims,
            demo_moments=[plan.variant_directions[1].creative_angle] if len(plan.variant_directions) > 1 else [plan.main_message],
            visual_assets_detected=[item.file_name for item in project.uploaded_files],
            brand_style_notes=plan.visual_style,
            safe_claims=plan.safe_claims,
            claims_to_avoid=plan.forbidden_claims or project.claims_to_avoid,
            recommended_ad_playbooks=[],
            recommended_video_formats=[project.platform, project.duration],
            recommended_hooks=[direction.creative_angle for direction in plan.variant_directions],
            recommended_cta=plan.cta or project.cta or "Learn more",
            confidence_score=0.8,
        )
        intelligence.recommended_ad_playbooks = self.playbook_engine.select_playbooks(intelligence)
        return intelligence

    def to_creative_angles(self, project: Project, plan: CreativePlan) -> list[CreativeAngle]:
        audience = project.audience or "target customers"
        angle_types = ["storytelling", "product_demo"]
        angles: list[CreativeAngle] = []
        for index, direction in enumerate(plan.variant_directions[:2]):
            angle_type = angle_types[index] if index < len(angle_types) else "product_demo"
            angles.append(
                CreativeAngle(
                    id=f"angle_{direction.id.removeprefix('direction_')}",
                    name=direction.name,
                    angle_type=angle_type,
                    target_audience=audience,
                    pain_point=plan.audience_pain,
                    emotional_trigger=direction.creative_angle if index == 0 else plan.main_message,
                    hook=direction.creative_angle,
                    product_role=plan.product_truth,
                    proof_demo_moment=direction.creative_angle if index == 1 else plan.main_message,
                    cta=plan.cta,
                    reason_why_it_can_work=direction.hypothesis,
                    score=92 - index * 3,
                    hypothesis=direction.hypothesis,
                    best_for_metric=direction.best_for_metric,
                )
            )
        return angles

    def _coerce_plan(self, data: dict[str, Any], project: Project, brief: ProductBrief, vision: VisionAnalysis) -> dict[str, Any]:
        directions = data.get("variant_directions")
        if not isinstance(directions, list) or len(directions) < 2:
            raise ValueError("Creative Plan must include exactly 2 variant_directions.")
        coerced_directions = [
            self._coerce_direction(directions[0], "Storytelling / Problem-led", "hook_rate"),
            self._coerce_direction(directions[1], "Product Demo / Benefit-led", "conversion_rate"),
        ]
        return {
            "product_truth": self._string(data.get("product_truth")) or brief.short_description,
            "audience_pain": self._string(data.get("audience_pain")) or brief.main_problem,
            "main_message": self._string(data.get("main_message")) or brief.main_benefit,
            "safe_claims": self._string_list(data.get("safe_claims")),
            "forbidden_claims": self._string_list(data.get("forbidden_claims")) or project.claims_to_avoid,
            "cta": self._string(data.get("cta")) or project.cta or "Learn more",
            "visual_style": self._string(data.get("visual_style")) or brief.recommended_visual_style or vision.detected_visual_style,
            "variant_directions": coerced_directions,
        }

    def _coerce_direction(self, raw: Any, name: str, metric: str) -> dict[str, str]:
        if not isinstance(raw, dict):
            raise ValueError("Creative Plan variant direction must be an object.")
        return {
            "name": self._string(raw.get("name")) or name,
            "hypothesis": self._string(raw.get("hypothesis")),
            "creative_angle": self._string(raw.get("creative_angle")),
            "best_for_metric": self._string(raw.get("best_for_metric")) or metric,
        }

    def _build_prompt(self, project: Project, brief: ProductBrief, vision: VisionAnalysis) -> str:
        payload = {
            "project": project.model_dump(mode="json"),
            "normalized_brief": brief.model_dump(mode="json"),
            "vision_analysis": vision.model_dump(mode="json"),
            "required_output_schema": {
                "product_truth": "what the product/app actually helps the user do, one sentence",
                "audience_pain": "one specific audience problem",
                "main_message": "one core ad message",
                "safe_claims": ["short safe claims allowed in copy"],
                "forbidden_claims": ["claims that must not appear"],
                "cta": "final CTA",
                "visual_style": "practical visual direction for UGC/video generation",
                "variant_directions": [
                    {
                        "name": "Storytelling / Problem-led",
                        "hypothesis": "why this direction can work",
                        "creative_angle": "the story/problem-led direction",
                        "best_for_metric": "hook_rate",
                    },
                    {
                        "name": "Product Demo / Benefit-led",
                        "hypothesis": "why this direction can work",
                        "creative_angle": "the demo/benefit-led direction",
                        "best_for_metric": "conversion_rate",
                    },
                ],
            },
        }
        return (
            "You are the Creative Plan Agent for a short-form AI ads video factory. "
            "Your job is to replace separate Product Intelligence and 5 Creative Angles with one compact production plan. "
            "Return JSON only, no markdown. Keep it short, practical, and directly useful for generating two video variants. "
            "Do not create 5 angles. Create exactly 2 variant_directions in this order: "
            "1) Storytelling / Problem-led, 2) Product Demo / Benefit-led. "
            "Do not repeat the same pain point/hook/CTA across layers. Keep one product truth, one audience pain, one main message. "
            "Respect claims_to_avoid. Avoid exaggerated or unsafe claims. "
            "For app products, make the demo direction practical for app screenshot/UI overlay production.\n\n"
            f"Input:\n{json.dumps(payload, ensure_ascii=False, indent=2)}"
        )

    def _string(self, value: Any) -> str:
        if isinstance(value, list):
            value = " ".join(str(item).strip() for item in value if str(item).strip())
        return str(value or "").strip()

    def _string_list(self, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return [self._string(item) for item in value if self._string(item)]
        return [item.strip() for item in str(value).replace("\n", ",").replace(";", ",").split(",") if item.strip()]
