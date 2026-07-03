from typing import Protocol

from app.models.schemas import AnalyzeProjectResponse, Project
from app.services.product_intelligence import ProductIntelligenceService
from app.services.vision_provider import GeminiVisionProvider, VisionProvider


class ProductAnalyzer(Protocol):
    def analyze(self, project: Project) -> AnalyzeProjectResponse:
        ...


class ProductIntelligenceAnalyzer:
    def __init__(
        self,
        vision_provider: VisionProvider | None = None,
        intelligence_service: ProductIntelligenceService | None = None,
    ) -> None:
        self.vision_provider = vision_provider or GeminiVisionProvider()
        self.intelligence_service = intelligence_service or ProductIntelligenceService()

    def analyze(self, project: Project) -> AnalyzeProjectResponse:
        vision = self.vision_provider.analyze_files(project)
        intelligence = self.intelligence_service.build(project, vision)
        product_brief = self.intelligence_service.to_product_brief(intelligence)

        return AnalyzeProjectResponse(
            product_intelligence=intelligence,
            product_brief=product_brief,
            vision_analysis=vision,
        )
