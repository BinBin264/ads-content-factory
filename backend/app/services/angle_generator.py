from typing import Protocol

from app.models.schemas import CreativeAngle, ProductBrief, ProductIntelligenceBrief, Project


class CreativeAngleGenerator(Protocol):
    def generate(
        self,
        project: Project,
        brief: ProductBrief,
        intelligence: ProductIntelligenceBrief | None = None,
    ) -> list[CreativeAngle]:
        ...


class RuleBasedCreativeAngleGenerator:
    def generate(
        self,
        project: Project,
        brief: ProductBrief,
        intelligence: ProductIntelligenceBrief | None = None,
    ) -> list[CreativeAngle]:
        intelligence = intelligence or self._fallback_intelligence(project, brief)
        cta = intelligence.recommended_cta or project.cta or self._default_cta(project.goal)
        audience = intelligence.primary_audience
        hooks = self._five_hooks(project, intelligence)
        pain_points = self._pad(intelligence.pain_points, "The audience needs a clearer way to understand the product.")
        triggers = self._pad(intelligence.emotional_triggers, "curiosity")
        demo_moments = self._pad(intelligence.demo_moments, "Show the product in use.")
        benefits = self._pad(intelligence.functional_benefits, intelligence.core_use_case)

        templates = [
            {
                "name": "Emotional discovery",
                "angle_type": "storytelling",
                "hook": hooks[0],
                "pain_point": pain_points[0],
                "emotional_trigger": triggers[0],
                "product_role": f"{project.product_name} turns a relatable moment into a useful next step.",
                "proof_demo_moment": demo_moments[0],
                "reason": "It starts with a human moment, then earns the demo instead of feeling like a pitch.",
                "score": 94,
            },
            {
                "name": "Product-led demo",
                "angle_type": "product_demo",
                "hook": hooks[1],
                "pain_point": pain_points[1],
                "emotional_trigger": triggers[1],
                "product_role": f"{project.product_name} is shown as the main action from setup to result.",
                "proof_demo_moment": demo_moments[1],
                "reason": "A direct demo makes the value easy to understand in a short paid social placement.",
                "score": 91,
            },
            {
                "name": "Problem-solution",
                "angle_type": "problem_solution",
                "hook": hooks[2],
                "pain_point": pain_points[2],
                "emotional_trigger": triggers[2],
                "product_role": f"{project.product_name} removes the specific friction shown in the setup.",
                "proof_demo_moment": demo_moments[2],
                "reason": "The viewer sees the problem first, so the product answer feels specific.",
                "score": 88,
            },
            {
                "name": "Hidden benefit",
                "angle_type": "curiosity",
                "hook": hooks[3],
                "pain_point": pain_points[0],
                "emotional_trigger": "curiosity",
                "product_role": f"{project.product_name} reveals a benefit viewers may not know to look for.",
                "proof_demo_moment": demo_moments[3],
                "reason": "The hook creates an open loop that the product demo can close.",
                "score": 85,
            },
            {
                "name": "Friend recommendation",
                "angle_type": "social_proof",
                "hook": hooks[4],
                "pain_point": pain_points[1],
                "emotional_trigger": "trust",
                "product_role": f"{project.product_name} is framed as the practical first thing a friend would suggest.",
                "proof_demo_moment": benefits[0],
                "reason": "Recommendation-style UGC lowers skepticism while staying native to TikTok, Reels, and Shorts.",
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

    def _five_hooks(self, project: Project, intelligence: ProductIntelligenceBrief) -> list[str]:
        hooks = list(intelligence.recommended_hooks)
        while len(hooks) < 5:
            hooks.append(f"Here's why {project.product_name} is worth checking before you decide.")
        return hooks[:5]

    def _pad(self, values: list[str], fallback: str) -> list[str]:
        padded = list(values)
        while len(padded) < 4:
            padded.append(fallback)
        return padded

    def _fallback_intelligence(self, project: Project, brief: ProductBrief) -> ProductIntelligenceBrief:
        return ProductIntelligenceBrief(
            detected_product=project.product_name,
            product_category=brief.category,
            product_type=brief.product_type,
            core_use_case=brief.short_description,
            target_audience_segments=brief.target_audience,
            primary_audience=", ".join(brief.target_audience) or project.audience or "practical buyers",
            pain_points=[brief.main_problem],
            emotional_triggers=brief.emotional_triggers,
            functional_benefits=brief.functional_benefits,
            proof_points=brief.proof_elements,
            demo_moments=brief.proof_elements,
            visual_assets_detected=[],
            brand_style_notes=brief.recommended_visual_style,
            safe_claims=brief.safe_claims,
            claims_to_avoid=brief.claims_to_avoid,
            recommended_ad_playbooks=[],
            recommended_video_formats=brief.recommended_ad_formats,
            recommended_hooks=[
                f"I tried {project.product_name} for this exact problem.",
                f"Here is how {project.product_name} works in 20 seconds.",
                f"If this feels annoying, {project.product_name} can help.",
                f"The best part about {project.product_name} is not obvious.",
                f"I would recommend {project.product_name} if you want a simpler first step.",
            ],
            recommended_cta=project.cta or self._default_cta(project.goal),
            confidence_score=0.5,
        )

    def _default_cta(self, goal: str) -> str:
        if goal == "app_install":
            return "Download now"
        if goal == "lead":
            return "Get started"
        if goal == "purchase":
            return "Shop now"
        return "Learn more"
