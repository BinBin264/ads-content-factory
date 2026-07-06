from typing import Protocol

from app.models.schemas import AnalyzeProjectResponse, Project
from app.services.creative_plan import BriefNormalizer, CreativePlanService
from app.services.creative_plan_generator import GeminiCreativePlanGenerator
from app.services.vision_provider import VisionProvider


class ProductAnalyzer(Protocol):
    def analyze(self, project: Project) -> AnalyzeProjectResponse:
        ...


class ProductIntelligenceAnalyzer:
    def __init__(
        self,
        vision_provider: VisionProvider | None = None,
        brief_normalizer: BriefNormalizer | None = None,
        creative_plan_service: CreativePlanService | None = None,
        creative_plan_generator: GeminiCreativePlanGenerator | None = None,
    ) -> None:
        self.creative_plan_generator = creative_plan_generator or GeminiCreativePlanGenerator(
            vision_provider=vision_provider,
            brief_normalizer=brief_normalizer,
            creative_plan_service=creative_plan_service,
        )

    def analyze(self, project: Project) -> AnalyzeProjectResponse:
        return self.creative_plan_generator.analyze(project)
