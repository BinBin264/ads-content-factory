from typing import Protocol

from app.models.schemas import CreativePlan, PlanCreationResult, Project
from app.services.creative_plan import BriefNormalizer, CreativePlanService
from app.services.vision_provider import GeminiVisionProvider, VisionProvider


class CreativePlanGenerator(Protocol):
    def generate(self, project: Project) -> CreativePlan:
        ...

    def create(self, project: Project) -> PlanCreationResult:
        ...


class GeminiCreativePlanGenerator:
    def __init__(
        self,
        vision_provider: VisionProvider | None = None,
        brief_normalizer: BriefNormalizer | None = None,
        creative_plan_service: CreativePlanService | None = None,
    ) -> None:
        self.vision_provider = vision_provider or GeminiVisionProvider()
        self.brief_normalizer = brief_normalizer or BriefNormalizer()
        self.creative_plan_service = creative_plan_service or CreativePlanService()

    def generate(self, project: Project) -> CreativePlan:
        result = self.create(project)
        if result.creative_plan is None:
            raise ValueError("Plan Creation generation did not return a creative_plan.")
        return result.creative_plan

    def create(self, project: Project) -> PlanCreationResult:
        vision = self.vision_provider.analyze_files(project)
        normalized_brief = self.brief_normalizer.normalize(project, vision)
        creative_plan = self.creative_plan_service.build(project, normalized_brief, vision)

        return PlanCreationResult(
            vision_analysis=vision,
            creative_plan=creative_plan,
        )
