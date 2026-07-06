import json
from typing import Any
from typing import Protocol

from app.models.schemas import CreativeAngle, ProductBrief, ProductIntelligenceBrief, Project
from app.services.intelligence_context import compact_intelligence_context, compact_project_context
from app.services.llm_provider import LLMProvider, build_llm_provider


class CreativeAngleGenerator(Protocol):
    def generate(
        self,
        project: Project,
        brief: ProductBrief,
        intelligence: ProductIntelligenceBrief | None = None,
    ) -> list[CreativeAngle]:
        ...


class GeminiCreativeAngleGenerator:
    ANGLE_TYPES = ["storytelling", "product_demo", "problem_solution", "curiosity", "social_proof"]

    RESPONSE_SCHEMA = {
        "type": "object",
        "properties": {
            "angles": {
                "type": "array",
                "minItems": 5,
                "maxItems": 5,
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "angle_type": {"type": "string"},
                        "target_audience": {"type": "string"},
                        "pain_point": {"type": "string"},
                        "emotional_trigger": {"type": "string"},
                        "hook": {"type": "string"},
                        "product_role": {"type": "string"},
                        "proof_demo_moment": {"type": "string"},
                        "cta": {"type": "string"},
                        "reason_why_it_can_work": {"type": "string"},
                        "score": {"type": "number"},
                    },
                    "required": [
                        "name",
                        "angle_type",
                        "target_audience",
                        "pain_point",
                        "emotional_trigger",
                        "hook",
                        "product_role",
                        "proof_demo_moment",
                        "cta",
                        "reason_why_it_can_work",
                        "score",
                    ],
                },
            }
        },
        "required": ["angles"],
    }

    def __init__(self, llm_provider: LLMProvider | None = None) -> None:
        self.llm_provider = llm_provider or build_llm_provider()

    def generate(
        self,
        project: Project,
        brief: ProductBrief,
        intelligence: ProductIntelligenceBrief | None = None,
    ) -> list[CreativeAngle]:
        if intelligence is None:
            raise ValueError("Product Intelligence is required before generating creative angles.")
        return self._generate_with_llm(project, intelligence)

    def _generate_with_llm(self, project: Project, intelligence: ProductIntelligenceBrief) -> list[CreativeAngle]:
        prompt = (
            "You are the Creative Angle Agent for TikTok, Reels, and Shorts. "
            "Generate exactly 5 meaningfully different short-form ad angles. "
            "Return JSON only in this exact shape: {\"angles\": [CreativeAngle...]}. "
            "Every CreativeAngle object must include these exact keys: "
            "name, angle_type, target_audience, pain_point, emotional_trigger, hook, "
            "product_role, proof_demo_moment, cta, reason_why_it_can_work, score. "
            "Required angle types in order: storytelling, product_demo, problem_solution, curiosity, social_proof. "
            "Hooks must be simple spoken language and strong in the first 2 seconds. "
            "Avoid generic hooks like Introducing or This product is amazing. "
            "Make every angle specific to the product intelligence.\n\n"
            f"Project:\n{json.dumps(compact_project_context(project), ensure_ascii=False, indent=2)}\n\n"
            f"Product intelligence:\n{json.dumps(compact_intelligence_context(intelligence), ensure_ascii=False, indent=2)}"
        )
        data = self.llm_provider.generate_json(prompt, temperature=0.65, response_schema=self.RESPONSE_SCHEMA)
        raw_angles = data.get("angles")
        if not isinstance(raw_angles, list) or len(raw_angles) < 5:
            raise ValueError("Gemini angle response must include at least 5 angles")
        return [
            CreativeAngle.model_validate(self._coerce_angle(item, index, project, intelligence))
            for index, item in enumerate(raw_angles[:5])
        ]

    def _coerce_angle(
        self,
        item: Any,
        index: int,
        project: Project,
        intelligence: ProductIntelligenceBrief,
    ) -> dict[str, Any]:
        if not isinstance(item, dict):
            raise ValueError(f"Gemini angle at index {index} must be an object")

        angle_type = self._string_from(item, "angle_type", "type", "category") or self.ANGLE_TYPES[index]
        angle_type = angle_type.lower().replace("-", "_").replace(" ", "_")
        if angle_type not in self.ANGLE_TYPES:
            angle_type = self.ANGLE_TYPES[index]

        hook = self._string_from(item, "hook", "opening_hook", "headline") or self._pick(
            intelligence.recommended_hooks,
            index,
            f"Here's what {project.product_name} can show you in seconds.",
        )
        pain_point = self._string_from(item, "pain_point", "problem", "pain", "viewer_problem") or self._pick(
            intelligence.pain_points,
            index,
            "The audience is unsure what to do next.",
        )
        emotional_trigger = self._string_from(item, "emotional_trigger", "emotion", "trigger") or self._pick(
            intelligence.emotional_triggers,
            index,
            "curiosity",
        )
        proof_demo_moment = self._string_from(item, "proof_demo_moment", "demo_moment", "proof", "demo") or self._pick(
            intelligence.demo_moments,
            index,
            self._pick(intelligence.proof_points, index, "Show the product working on screen."),
        )

        return {
            "name": self._string_from(item, "name", "title", "angle_name") or self._title_from_type(angle_type),
            "angle_type": angle_type,
            "target_audience": self._string_from(item, "target_audience", "audience", "target") or intelligence.primary_audience,
            "pain_point": pain_point,
            "emotional_trigger": emotional_trigger,
            "hook": hook,
            "product_role": self._string_from(item, "product_role", "role", "solution_role")
            or f"{project.product_name} is the tool that turns the hook into a concrete next step.",
            "proof_demo_moment": proof_demo_moment,
            "cta": self._string_from(item, "cta", "call_to_action") or intelligence.recommended_cta or project.cta or self._default_cta(project.goal),
            "reason_why_it_can_work": self._string_from(item, "reason_why_it_can_work", "reason", "why_it_works")
            or "It connects a specific viewer problem to a clear product demo and CTA.",
            "score": self._score_from(item.get("score"), index),
        }

    def _string_from(self, item: dict[str, Any], *keys: str) -> str:
        for key in keys:
            value = item.get(key)
            if value is None:
                continue
            if isinstance(value, list):
                value = ", ".join(str(part).strip() for part in value if str(part).strip())
            value = str(value).strip()
            if value:
                return value
        return ""

    def _pick(self, values: list[str], index: int, default_value: str) -> str:
        return values[index % len(values)] if values else default_value

    def _title_from_type(self, angle_type: str) -> str:
        return angle_type.replace("_", " ").title()

    def _score_from(self, value: Any, index: int) -> float:
        try:
            score = float(value)
        except (TypeError, ValueError):
            score = 88 - index * 3
        if 0 < score <= 1:
            score *= 100
        elif 1 < score <= 10:
            score *= 10
        return max(0, min(100, score))

    def _default_cta(self, goal: str) -> str:
        if goal == "app_install":
            return "Download now"
        if goal == "lead":
            return "Get started"
        if goal == "purchase":
            return "Shop now"
        return "Learn more"
