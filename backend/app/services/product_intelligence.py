import json

from app.models.schemas import ProductBrief, ProductIntelligenceBrief, Project, VisionAnalysis
from app.services.llm_provider import LLMProvider, build_llm_provider
from app.services.playbook_engine import PlaybookEngine


def _first(values: list[str], default: str) -> str:
    return values[0] if values else default


class ProductIntelligenceService:
    def __init__(
        self,
        playbook_engine: PlaybookEngine | None = None,
        llm_provider: LLMProvider | None = None,
    ) -> None:
        self.playbook_engine = playbook_engine or PlaybookEngine()
        self.llm_provider = llm_provider or build_llm_provider()

    def build(self, project: Project, vision: VisionAnalysis) -> ProductIntelligenceBrief:
        return self._build_with_llm(project, vision)

    def _build_with_llm(self, project: Project, vision: VisionAnalysis) -> ProductIntelligenceBrief:
        prompt = self._build_prompt(project, vision)
        data = self.llm_provider.generate_json(prompt, temperature=0.25)
        data = self._coerce_llm_data(data, vision)
        intelligence = ProductIntelligenceBrief.model_validate(data)
        if not intelligence.recommended_ad_playbooks:
            intelligence.recommended_ad_playbooks = self.playbook_engine.select_playbooks(intelligence)
        return intelligence

    def _coerce_llm_data(self, data: dict, vision: VisionAnalysis) -> dict:
        product_type = str(data.get("product_type") or vision.detected_product_type).lower().replace(" ", "_")
        product_type_aliases = {
            "mobile": "mobile_app",
            "mobileapp": "mobile_app",
            "app": "mobile_app",
            "food": "fnb",
            "food_and_beverage": "fnb",
            "f&b": "fnb",
            "educational": "education",
            "education_app": "education",
            "e-commerce": "ecommerce",
            "e_commerce": "ecommerce",
        }
        data["product_type"] = product_type_aliases.get(product_type, product_type)
        if data["product_type"] not in {"mobile_app", "skincare", "fnb", "ecommerce", "education", "general"}:
            data["product_type"] = vision.detected_product_type

        confidence = data.get("confidence_score", vision.confidence)
        if isinstance(confidence, (int, float)) and confidence > 1:
            confidence = confidence / 100
        data["confidence_score"] = confidence

        if not isinstance(data.get("recommended_ad_playbooks"), list):
            data["recommended_ad_playbooks"] = []
        if data["recommended_ad_playbooks"] and isinstance(data["recommended_ad_playbooks"][0], str):
            data["recommended_ad_playbooks"] = []

        return data

    def _build_prompt(self, project: Project, vision: VisionAnalysis) -> str:
        payload = {
            "project": project.model_dump(mode="json"),
            "vision_analysis": vision.model_dump(mode="json"),
            "allowed_product_types": ["mobile_app", "skincare", "fnb", "ecommerce", "education", "general"],
            "required_output_schema": {
                "detected_product": "string",
                "product_category": "string",
                "product_type": "mobile_app | skincare | fnb | ecommerce | education | general",
                "core_use_case": "string",
                "target_audience_segments": ["string"],
                "primary_audience": "string",
                "pain_points": ["string"],
                "emotional_triggers": ["string"],
                "functional_benefits": ["string"],
                "proof_points": ["string"],
                "demo_moments": ["string"],
                "visual_assets_detected": ["string"],
                "brand_style_notes": "string",
                "safe_claims": ["string"],
                "claims_to_avoid": ["string"],
                "recommended_ad_playbooks": [
                    {
                        "playbook_id": "string",
                        "name": "string",
                        "best_for": ["string"],
                        "structure": ["string"],
                        "recommended_angles": ["string"],
                        "scene_formula": ["string"],
                    }
                ],
                "recommended_hooks": ["string"],
                "recommended_cta": "string",
            },
        }
        return (
            "You are the Product Intelligence Agent for an AI ads video factory. "
            "Analyze the product and assets. Return JSON only, no markdown. "
            "Be specific to the product. Avoid generic marketing language. "
            "Respect claims_to_avoid and use safe claims. "
            "For app products, focus on problem -> app demo -> result -> CTA. "
            "For skincare, focus on routine, texture, and realistic expectation. "
            "For F&B, focus on craving, close-up, taste reaction, and order CTA. "
            "For education, focus on learning pain, practice method, and small win.\n\n"
            f"Input:\n{json.dumps(payload, ensure_ascii=False, indent=2)}"
        )

    def to_product_brief(self, intelligence: ProductIntelligenceBrief) -> ProductBrief:
        return ProductBrief(
            product_name=intelligence.detected_product,
            category=intelligence.product_category,
            product_type=intelligence.product_type,
            short_description=intelligence.core_use_case,
            target_audience=intelligence.target_audience_segments,
            main_problem=_first(intelligence.pain_points, "The audience needs a clearer way to understand the product value."),
            main_benefit=_first(intelligence.functional_benefits, intelligence.core_use_case),
            emotional_triggers=intelligence.emotional_triggers,
            functional_benefits=intelligence.functional_benefits,
            proof_elements=intelligence.proof_points,
            safe_claims=intelligence.safe_claims,
            claims_to_avoid=intelligence.claims_to_avoid,
            recommended_visual_style=intelligence.brand_style_notes,
            recommended_ad_formats=[playbook.name for playbook in intelligence.recommended_ad_playbooks],
        )
