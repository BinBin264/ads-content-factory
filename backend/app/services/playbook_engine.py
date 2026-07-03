from app.models.schemas import Playbook, ProductIntelligenceBrief
from app.services.playbooks import get_playbooks_for_type


class PlaybookEngine:
    def select_playbooks(self, intelligence: ProductIntelligenceBrief) -> list[Playbook]:
        playbooks = get_playbooks_for_type(intelligence.product_type)
        if not playbooks:
            return get_playbooks_for_type("general")
        return playbooks
