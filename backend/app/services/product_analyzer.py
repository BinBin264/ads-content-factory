from typing import Protocol

from app.models.schemas import ProductBrief, Project


class ProductAnalyzer(Protocol):
    def analyze(self, project: Project) -> ProductBrief:
        ...


def _lower_join(*values: str | None) -> str:
    return " ".join(value or "" for value in values).lower()


def _split_claims(value: list[str] | str | None) -> list[str]:
    if not value:
        return []
    if isinstance(value, list):
        return value
    normalized = value.replace("\n", ",").replace(";", ",")
    return [item.strip() for item in normalized.split(",") if item.strip()]


class RuleBasedProductAnalyzer:
    def analyze(self, project: Project) -> ProductBrief:
        category_text = _lower_join(project.product_category, project.product_name, project.product_description)
        category = project.product_category or self._infer_category(category_text)
        audience = project.audience or self._infer_audience(category_text)
        description = project.product_description or f"{project.product_name} helps {audience} get a better daily outcome."

        if self._is_app(category_text):
            return ProductBrief(
                product_name=project.product_name,
                category=category,
                product_type="Mobile app / SaaS",
                short_description=description,
                target_audience=audience,
                main_problem="Users want a faster, simpler way to complete the job without switching between messy tools.",
                main_benefit="A guided app flow that turns the task into a clear next action.",
                emotional_triggers=["relief", "control", "momentum"],
                functional_benefits=["clean workflow", "quick setup", "visible progress", "mobile-first experience"],
                proof_elements=["screen recording demo", "before and after workflow", "feature close-up"],
                safe_claims=["Designed to simplify the workflow", "Helps users save time on repetitive steps"],
                claims_to_avoid=_split_claims(project.claims_to_avoid),
                recommended_visual_style="Realistic phone-in-hand UGC, screen capture inserts, fast captions, clear UI zooms.",
                recommended_ad_formats=["Problem -> App demo -> Result -> CTA", "Screen-recorded tutorial", "Creator testimonial"],
            )

        if "skincare" in category_text or "beauty" in category_text or "serum" in category_text:
            return ProductBrief(
                product_name=project.product_name,
                category=category,
                product_type="Skincare product",
                short_description=description,
                target_audience=audience,
                main_problem="The audience wants a routine that feels easy, trustworthy, and gentle.",
                main_benefit="A simple product moment that fits into an everyday care routine.",
                emotional_triggers=["confidence", "self-care", "freshness"],
                functional_benefits=["easy routine step", "pleasant texture", "daily-use positioning"],
                proof_elements=["texture macro", "routine demo", "mirror reaction"],
                safe_claims=["Supports a consistent routine", "Leaves skin looking refreshed"],
                claims_to_avoid=_split_claims(project.claims_to_avoid),
                recommended_visual_style="Soft natural bathroom light, texture close-ups, realistic routine shots.",
                recommended_ad_formats=["Pain point -> Routine/demo -> Texture/result expectation -> CTA"],
            )

        if any(token in category_text for token in ["food", "drink", "f&b", "beverage", "restaurant", "snack", "coffee"]):
            return ProductBrief(
                product_name=project.product_name,
                category=category,
                product_type="Food and beverage",
                short_description=description,
                target_audience=audience,
                main_problem="The audience wants something satisfying now, but needs a strong reason to choose this product.",
                main_benefit="A craving-led product moment with sensory detail and a clear offer.",
                emotional_triggers=["craving", "delight", "reward"],
                functional_benefits=["appealing taste cues", "easy ordering", "shareable moment"],
                proof_elements=["close-up bite or pour", "reaction shot", "limited offer card"],
                safe_claims=["Made for a satisfying treat", "Great for a quick break"],
                claims_to_avoid=_split_claims(project.claims_to_avoid),
                recommended_visual_style="Bright product close-ups, handheld reaction, quick cuts, appetizing sound cues.",
                recommended_ad_formats=["Craving -> Product close-up -> Reaction -> Offer/CTA"],
            )

        return ProductBrief(
            product_name=project.product_name,
            category=category,
            product_type="Consumer product",
            short_description=description,
            target_audience=audience,
            main_problem="The audience has a recurring need but may not know which product is worth trying.",
            main_benefit="A clear product demo that makes the value easy to understand in seconds.",
            emotional_triggers=["curiosity", "confidence", "convenience"],
            functional_benefits=["simple demonstration", "clear use case", "easy decision path"],
            proof_elements=["hands-on demo", "comparison moment", "creator recommendation"],
            safe_claims=["Designed for everyday use", "Helps make the routine easier"],
            claims_to_avoid=_split_claims(project.claims_to_avoid),
            recommended_visual_style="General UGC product demo with natural light, close-ups, and concise captions.",
            recommended_ad_formats=["Hook -> Product demo -> Benefit proof -> CTA"],
        )

    def _infer_category(self, text: str) -> str:
        if self._is_app(text):
            return "Mobile app"
        if "skincare" in text or "beauty" in text:
            return "Skincare"
        if any(token in text for token in ["food", "drink", "coffee", "snack"]):
            return "F&B"
        return "General product"

    def _infer_audience(self, text: str) -> str:
        if self._is_app(text):
            return "busy mobile users"
        if "skincare" in text or "beauty" in text:
            return "people building a simple daily skincare routine"
        if any(token in text for token in ["food", "drink", "coffee", "snack"]):
            return "people looking for a quick, satisfying treat"
        return "practical buyers comparing simple solutions"

    def _is_app(self, text: str) -> bool:
        return any(token in text for token in ["app", "mobile", "screenshot", "saas", "software", "dashboard"])
