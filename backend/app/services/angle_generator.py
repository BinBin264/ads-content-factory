from typing import Protocol

from app.models.schemas import CreativeAngle, ProductBrief, Project


class CreativeAngleGenerator(Protocol):
    def generate(self, project: Project, brief: ProductBrief) -> list[CreativeAngle]:
        ...


class RuleBasedCreativeAngleGenerator:
    def generate(self, project: Project, brief: ProductBrief) -> list[CreativeAngle]:
        if self._is_coin_scanner(project, brief):
            return self._generate_coin_scanner_angles(project, brief)

        cta = project.cta or self._default_cta(project.goal)
        audience = self._audience_text(project, brief)
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

    def _is_coin_scanner(self, project: Project, brief: ProductBrief) -> bool:
        text = " ".join(
            [
                project.product_name,
                project.product_category or "",
                project.product_description or "",
                brief.product_type,
                brief.short_description,
            ]
        ).lower()
        return "coin" in text and any(token in text for token in ["scan", "scanner", "identify", "value", "app"])

    def _generate_coin_scanner_angles(self, project: Project, brief: ProductBrief) -> list[CreativeAngle]:
        cta = project.cta or "Download now and scan your old coins"
        audience = self._audience_text(project, brief)
        templates = [
            {
                "name": "Almost spent it",
                "angle_type": "storytelling",
                "pain_point": "People treat old coins like loose change because they do not know what they are.",
                "emotional_trigger": "surprise",
                "hook": "I almost spent this coin...",
                "product_role": "The app turns a random coin discovery into a quick scan-and-check moment.",
                "proof_demo_moment": "scan the coin with the phone camera and show the coin detail result screen",
                "reason": "The hook creates instant curiosity without promising the coin is valuable.",
                "score": 94,
            },
            {
                "name": "Five-second coin check",
                "angle_type": "product_demo",
                "pain_point": "Users want a fast way to check an old coin before searching random websites.",
                "emotional_trigger": "curiosity",
                "hook": "Here's how to check an old coin in 5 seconds.",
                "product_role": "The app is shown as the simple scan workflow from camera to coin details.",
                "proof_demo_moment": "open the app, scan the coin, and reveal estimated reference value as a research cue",
                "reason": "A direct demo makes the app install value obvious in a short ad.",
                "score": 92,
            },
            {
                "name": "Coin jar mystery",
                "angle_type": "problem_solution",
                "pain_point": "A jar of old coins is interesting, but most people do not know where to start.",
                "emotional_trigger": "discovery",
                "hook": "That old coin jar might be more interesting than you think.",
                "product_role": "The app gives users a practical first step: scan, identify, and save the details.",
                "proof_demo_moment": "pick one coin from a jar and compare the physical coin to the app details",
                "reason": "It connects a common household object to an easy app demo.",
                "score": 88,
            },
            {
                "name": "Hidden details",
                "angle_type": "curiosity",
                "pain_point": "Users miss dates, mint marks, and details that matter because they do not know what to inspect.",
                "emotional_trigger": "curiosity",
                "hook": "The tiny detail on this coin is what I wanted to check.",
                "product_role": "The app helps surface coin details that are hard for casual users to interpret.",
                "proof_demo_moment": "macro shot of coin date or mark followed by app detail screen",
                "reason": "A specific detail keeps the viewer watching for the scan result.",
                "score": 85,
            },
            {
                "name": "Collector friend recommendation",
                "angle_type": "social_proof",
                "pain_point": "Casual users need a low-pressure tool before asking collectors or searching forums.",
                "emotional_trigger": "confidence",
                "hook": "If you keep finding old coins, this is the first app I would try.",
                "product_role": "The app is framed as a friendly first check, not a guaranteed appraisal.",
                "proof_demo_moment": "creator scans two different coins and shows organized detail screens",
                "reason": "Recommendation-style UGC feels native while staying safe about value claims.",
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

    def _audience_text(self, project: Project, brief: ProductBrief) -> str:
        if project.audience:
            return project.audience
        if brief.target_audience:
            return ", ".join(brief.target_audience)
        return "practical buyers comparing simple solutions"
