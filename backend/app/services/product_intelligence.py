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

    def _build_rule_based(self, project: Project, vision: VisionAnalysis) -> ProductIntelligenceBrief:
        product_type = vision.detected_product_type
        category = project.product_category or self._category_name(product_type)
        audience_segments = self._audiences(project, product_type)
        claims_to_avoid = project.claims_to_avoid or self._default_claims_to_avoid(product_type)
        intelligence = ProductIntelligenceBrief(
            detected_product=project.product_name,
            product_category=category,
            product_type=product_type,
            core_use_case=self._core_use_case(project, product_type),
            target_audience_segments=audience_segments,
            primary_audience=_first(audience_segments, "practical buyers comparing simple solutions"),
            pain_points=self._pain_points(project, product_type),
            emotional_triggers=self._emotional_triggers(product_type),
            functional_benefits=self._functional_benefits(project, product_type),
            proof_points=self._proof_points(product_type),
            demo_moments=self._demo_moments(product_type),
            visual_assets_detected=vision.detected_objects + vision.detected_ui_elements,
            brand_style_notes=self._brand_style_notes(project, vision),
            safe_claims=self._safe_claims(product_type),
            claims_to_avoid=claims_to_avoid,
            recommended_ad_playbooks=[],
            recommended_video_formats=self._video_formats(product_type),
            recommended_hooks=self._hooks(project, product_type),
            recommended_cta=project.cta or self._default_cta(project.goal),
            confidence_score=vision.confidence,
        )
        intelligence.recommended_ad_playbooks = self.playbook_engine.select_playbooks(intelligence)
        return intelligence

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
                "recommended_video_formats": ["string"],
                "recommended_hooks": ["string"],
                "recommended_cta": "string",
                "confidence_score": 0.0,
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

    def _category_name(self, product_type: str) -> str:
        return {
            "mobile_app": "Mobile app",
            "skincare": "Skincare",
            "fnb": "F&B",
            "ecommerce": "Ecommerce product",
            "education": "Education",
        }.get(product_type, "General product")

    def _audiences(self, project: Project, product_type: str) -> list[str]:
        if project.audience:
            return [part.strip() for part in project.audience.replace(";", ",").split(",") if part.strip()]
        defaults = {
            "mobile_app": ["busy mobile users", "people who want a fast utility on their phone"],
            "skincare": ["young adults with skin texture concerns", "people building a simple skincare routine"],
            "fnb": ["office workers", "students", "people looking for a quick treat"],
            "ecommerce": ["online shoppers", "people comparing practical everyday products"],
            "education": ["beginner learners", "people practicing a new skill in short sessions"],
        }
        return defaults.get(product_type, ["practical buyers comparing simple solutions"])

    def _core_use_case(self, project: Project, product_type: str) -> str:
        if project.product_description:
            return project.product_description
        if product_type == "mobile_app":
            return f"Use {project.product_name} to complete a practical mobile task faster."
        if product_type == "skincare":
            return f"Add {project.product_name} into a realistic daily skincare routine."
        if product_type == "fnb":
            return f"Choose {project.product_name} for a satisfying craving or quick break."
        if product_type == "education":
            return f"Use {project.product_name} to practice a small learning task consistently."
        if product_type == "ecommerce":
            return f"Use {project.product_name} to solve a practical product need."
        return f"Understand and try {project.product_name} through a simple product demo."

    def _pain_points(self, project: Project, product_type: str) -> list[str]:
        text = f"{project.product_name} {project.product_description or ''}".lower()
        if "coin" in text:
            return [
                "Users do not know whether an old coin is worth researching.",
                "Users may accidentally spend or ignore collectible coins.",
                "Users do not know which coin details to look up first.",
            ]
        if product_type == "skincare":
            return [
                "Users feel frustrated by rough or bumpy-looking skin.",
                "Users do not want a complicated routine.",
                "Users need realistic expectations instead of miracle claims.",
            ]
        if product_type == "fnb":
            return [
                "Users have a craving for a satisfying drink or snack during a low-energy moment.",
                "Users need a clear reason to order now.",
                "Users want taste cues before they buy.",
            ]
        if product_type == "education":
            return [
                "Learners feel stuck because the learning practice feels awkward or too difficult.",
                "Learners need a small win that proves they can improve.",
                "Learners want short practice sessions that fit into the day.",
            ]
        if product_type == "ecommerce":
            return [
                "Buyers are unsure whether the product will solve their exact problem.",
                "Buyers want to see the product used before purchasing.",
                "Buyers need proof that the product fits everyday use.",
            ]
        if product_type == "mobile_app":
            return [
                "Users want a faster way to complete the task on their phone.",
                "Users are tired of guessing or searching manually.",
                "Users need a clear result in seconds.",
            ]
        return ["The audience needs a clear reason to care before trying the product."]

    def _emotional_triggers(self, product_type: str) -> list[str]:
        return {
            "mobile_app": ["curiosity", "relief", "control"],
            "skincare": ["confidence", "self-care", "freshness"],
            "fnb": ["craving", "reward", "comfort"],
            "ecommerce": ["confidence", "convenience", "satisfaction"],
            "education": ["progress", "confidence", "momentum"],
        }.get(product_type, ["curiosity", "confidence", "convenience"])

    def _functional_benefits(self, project: Project, product_type: str) -> list[str]:
        text = f"{project.product_name} {project.product_description or ''}".lower()
        if "coin" in text:
            return ["scan old coins", "identify coin details", "view estimated reference value", "know what to research next"]
        return {
            "mobile_app": ["quick mobile workflow", "clear next step", "visible app result"],
            "skincare": ["simple routine step", "lightweight application", "helps improve the look of texture"],
            "fnb": ["creamy taste cue", "easy delivery or ordering", "visual product appeal"],
            "ecommerce": ["hands-on product use", "clear feature demo", "practical everyday result"],
            "education": ["short practice flow", "guided method", "small learning win"],
        }.get(product_type, ["clear product use", "simple benefit", "easy CTA"])

    def _proof_points(self, product_type: str) -> list[str]:
        return {
            "mobile_app": ["screen demo", "result screen", "step-by-step app flow"],
            "skincare": ["texture close-up", "application demo", "routine placement"],
            "fnb": ["product close-up", "pour or sip moment", "reaction shot"],
            "ecommerce": ["unboxing", "feature close-up", "before and after use"],
            "education": ["lesson screen", "practice prompt", "small win result"],
        }.get(product_type, ["hands-on demo", "creator explanation", "product close-up"])

    def _demo_moments(self, product_type: str) -> list[str]:
        return {
            "mobile_app": ["Show the object or problem", "Open the app", "Use the key feature", "Show the result screen"],
            "skincare": ["Show skin concern", "Show product texture", "Apply in routine", "Show realistic expectation"],
            "fnb": ["Show craving moment", "Show product close-up", "Show sip or bite", "Show ordering CTA"],
            "ecommerce": ["Unbox product", "Show key feature", "Use product", "Show practical result"],
            "education": ["Show learning pain", "Open lesson or app", "Practice one prompt", "Show a small win"],
        }.get(product_type, ["Hook", "Problem", "Product demo", "Result and CTA"])

    def _safe_claims(self, product_type: str) -> list[str]:
        return {
            "mobile_app": ["Helps users complete the task faster", "Shows a useful reference result"],
            "skincare": ["Helps improve the look of rough texture", "Fits into a daily routine", "Results vary by person"],
            "fnb": ["Made for a satisfying treat", "Available for ordering or delivery"],
            "ecommerce": ["Designed for everyday use", "Helps solve a practical problem"],
            "education": ["Helps users practice consistently", "Supports beginner learning"],
        }.get(product_type, ["Designed for everyday use", "Helps make the task easier"])

    def _default_claims_to_avoid(self, product_type: str) -> list[str]:
        return {
            "mobile_app": ["guaranteed result", "100% accurate", "instant profit"],
            "skincare": ["cures acne", "guaranteed clear skin overnight", "medical claims"],
            "fnb": ["health claims", "medical benefits"],
            "education": ["become fluent instantly", "guaranteed mastery"],
        }.get(product_type, ["guaranteed results", "unverified claims"])

    def _video_formats(self, product_type: str) -> list[str]:
        if product_type == "mobile_app":
            return ["9:16 UGC app demo", "screen recording with creator intro", "problem-to-result short"]
        if product_type == "skincare":
            return ["9:16 routine demo", "texture close-up", "creator mirror setup"]
        if product_type == "fnb":
            return ["9:16 craving close-up", "making-of drink shot", "reaction ad"]
        if product_type == "education":
            return ["9:16 lesson demo", "before/after learning moment", "practice prompt ad"]
        return ["9:16 UGC demo", "1:1 feed cutdown"]

    def _hooks(self, project: Project, product_type: str) -> list[str]:
        text = f"{project.product_name} {project.product_description or ''}".lower()
        if "coin" in text:
            return [
                "I almost spent this old coin...",
                "Here's how to check an old coin in 5 seconds.",
                "Don't ignore the coins sitting in your drawer.",
                "I had no idea what this coin was until I scanned it.",
                "My dad told me to check old coins before spending them.",
            ]
        if product_type == "skincare":
            return [
                "My skin looked bumpy until I changed one step.",
                "Here's how I use this serum in my night routine.",
                "If your skin feels rough, try checking this.",
            ]
        if product_type == "fnb":
            return [
                "This is my new 3 PM energy fix.",
                "Watch this drink being made from start to finish.",
                "If you need a cold afternoon treat, look at this.",
            ]
        if product_type == "education":
            return [
                "I kept freezing when I tried to speak German.",
                "Here's one tiny practice trick that helped me start.",
                "If language apps feel boring, try this practice flow.",
            ]
        return [f"Here's the part of {project.product_name} I would show first."]

    def _default_cta(self, goal: str) -> str:
        if goal == "purchase":
            return "Shop now"
        if goal == "lead":
            return "Get started"
        if goal == "awareness":
            return "Learn more"
        return "Download now"

    def _brand_style_notes(self, project: Project, vision: VisionAnalysis) -> str:
        colors = f" Brand colors: {', '.join(project.brand_colors)}." if project.brand_colors else ""
        return f"{vision.detected_visual_style}.{colors} Keep claims realistic and captions easy to read."
