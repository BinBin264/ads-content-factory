from typing import Protocol

from app.models.schemas import CreativeAngle, CreativePlan, ProductBrief, ProductIntelligenceBrief, Project
from app.services.creative_plan import BriefNormalizer, CreativePlanService


class CreativeAngleGenerator(Protocol):
    def generate(
        self,
        project: Project,
        brief: ProductBrief,
        intelligence: ProductIntelligenceBrief | None = None,
        creative_plan: CreativePlan | None = None,
    ) -> list[CreativeAngle]:
        ...


class GeminiCreativeAngleGenerator:
    """Backward-compatible adapter.

    The old pipeline generated five angles here. The simplified pipeline now
    generates a single Creative Plan and maps its two variant directions into
    two legacy CreativeAngle records for older services/UI contracts.
    """

    def __init__(self, creative_plan_service: CreativePlanService | None = None) -> None:
        self.creative_plan_service = creative_plan_service or CreativePlanService()
        self.brief_normalizer = BriefNormalizer()

    def generate(
        self,
        project: Project,
        brief: ProductBrief,
        intelligence: ProductIntelligenceBrief | None = None,
        creative_plan: CreativePlan | None = None,
    ) -> list[CreativeAngle]:
        plan = creative_plan or project.creative_plan
        if plan is None:
            raise ValueError("Generate Creative Plan before generating variant directions.")
        return self.creative_plan_service.to_creative_angles(project, plan)
