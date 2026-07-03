from typing import Protocol

from app.models.schemas import CreativeAngle, ProductBrief, Project


class CreativeAngleGenerator(Protocol):
    def generate(self, project: Project, brief: ProductBrief) -> list[CreativeAngle]:
        ...


class RuleBasedCreativeAngleGenerator:
    def generate(self, project: Project, brief: ProductBrief) -> list[CreativeAngle]:
        cta = project.cta or self._default_cta(project.goal)
        audience = project.audience or brief.target_audience
        product = project.product_name

        templates = [
            {
                "name": "The moment it finally clicks",
                "angle_type": "Storytelling / emotional",
                "pain_point": brief.main_problem,
                "emotional_trigger": brief.emotional_triggers[0] if brief.emotional_triggers else "relief",
                "hook": f"I did not realize {product} could make this feel this simple.",
                "product_role": "The product appears as the turning point in a relatable daily story.",
                "proof_demo_moment": brief.proof_elements[0] if brief.proof_elements else "hands-on demo",
                "reason": "A personal story lowers resistance before the product demo appears.",
                "score": 91,
            },
            {
                "name": "Show me, do not tell me",
                "angle_type": "Product-led demo",
                "pain_point": "People need to understand the benefit before they care about the brand.",
                "emotional_trigger": "clarity",
                "hook": f"Here is exactly how {product} works in 20 seconds.",
                "product_role": "The product is the hero from the first visual beat.",
                "proof_demo_moment": brief.proof_elements[0] if brief.proof_elements else "close-up feature demo",
                "reason": "A direct demo is easy to reuse across paid social placements.",
                "score": 88,
            },
            {
                "name": "Fix the annoying part",
                "angle_type": "Problem-solution",
                "pain_point": brief.main_problem,
                "emotional_trigger": brief.emotional_triggers[0] if brief.emotional_triggers else "frustration",
                "hook": f"If this part of your routine feels annoying, try {product}.",
                "product_role": "The product removes the friction shown in the setup.",
                "proof_demo_moment": brief.proof_elements[1] if len(brief.proof_elements) > 1 else "before and after moment",
                "reason": "The audience sees the problem first, so the solution feels earned.",
                "score": 86,
            },
            {
                "name": "The hidden benefit",
                "angle_type": "Curiosity / hidden benefit",
                "pain_point": "The audience may overlook a benefit that is not obvious from the product name.",
                "emotional_trigger": "curiosity",
                "hook": f"The best part about {product} is not what you expect.",
                "product_role": "The product reveals an unexpected practical payoff.",
                "proof_demo_moment": brief.proof_elements[-1] if brief.proof_elements else "surprising use case",
                "reason": "Curiosity hooks can earn a longer watch time before the CTA.",
                "score": 84,
            },
            {
                "name": "Friend recommendation",
                "angle_type": "Social proof / recommendation",
                "pain_point": "Buyers hesitate when they do not know what to trust.",
                "emotional_trigger": "trust",
                "hook": f"I would recommend {product} to anyone who wants {brief.main_benefit.lower()}",
                "product_role": "The product is framed as a practical recommendation from a real user.",
                "proof_demo_moment": "creator testimonial plus product demo",
                "reason": "Recommendation-style ads feel native to UGC feeds.",
                "score": 82,
            },
        ]

        return [
            CreativeAngle(
                name=item["name"],
                angle_type=item["angle_type"],
                target_audience=audience,
                pain_point=item["pain_point"],
                emotional_trigger=item["emotional_trigger"],
                hook=item["hook"],
                product_role=item["product_role"],
                proof_demo_moment=item["proof_demo_moment"],
                cta=cta,
                reason_why_it_can_work=item["reason"],
                score=item["score"],
            )
            for item in templates
        ]

    def _default_cta(self, goal: str) -> str:
        if goal == "app_install":
            return "Download now"
        if goal == "lead":
            return "Get started"
        if goal == "purchase":
            return "Shop now"
        return "Learn more"
