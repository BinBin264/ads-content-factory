from app.models.schemas import Playbook

from app.services.playbooks.app_playbook import get_app_playbooks
from app.services.playbooks.education_playbook import get_education_playbooks
from app.services.playbooks.ecommerce_playbook import get_ecommerce_playbooks
from app.services.playbooks.fnb_playbook import get_fnb_playbooks
from app.services.playbooks.general_playbook import get_general_playbooks
from app.services.playbooks.skincare_playbook import get_skincare_playbooks


def get_playbooks_for_type(product_type: str) -> list[Playbook]:
    if product_type == "mobile_app":
        return get_app_playbooks()
    if product_type == "skincare":
        return get_skincare_playbooks()
    if product_type == "fnb":
        return get_fnb_playbooks()
    if product_type == "ecommerce":
        return get_ecommerce_playbooks()
    if product_type == "education":
        return get_education_playbooks()
    return get_general_playbooks()
