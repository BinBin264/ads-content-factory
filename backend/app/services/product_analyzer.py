from typing import Protocol

from app.models.schemas import AnalyzeProjectResponse, Project
from app.services.creative_plan import BriefNormalizer, CreativePlanService
from app.services.vision_provider import GeminiVisionProvider, VisionProvider


class ProductAnalyzer(Protocol):
    def analyze(self, project: Project) -> AnalyzeProjectResponse:
        ...


class ProductIntelligenceAnalyzer:
    def __init__(
        self,
        vision_provider: VisionProvider | None = None,
        brief_normalizer: BriefNormalizer | None = None,
        creative_plan_service: CreativePlanService | None = None,
    ) -> None:
        self.vision_provider = vision_provider or GeminiVisionProvider()
        self.brief_normalizer = brief_normalizer or BriefNormalizer()
        self.creative_plan_service = creative_plan_service or CreativePlanService()

    def analyze(self, project: Project) -> AnalyzeProjectResponse:
        vision = self.vision_provider.analyze_files(project)
        normalized_brief = self.brief_normalizer.normalize(project, vision)
        creative_plan = self.creative_plan_service.build(project, normalized_brief, vision)
        product_brief = self.creative_plan_service.to_product_brief(project, normalized_brief, creative_plan)
        intelligence = self.creative_plan_service.to_product_intelligence(project, product_brief, creative_plan)

        return AnalyzeProjectResponse(
            product_intelligence=intelligence,
            product_brief=product_brief,
            vision_analysis=vision,
            creative_plan=creative_plan,
        )
