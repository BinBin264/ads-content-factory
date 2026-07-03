from app.models.schemas import Playbook


def get_fnb_playbooks() -> list[Playbook]:
    return [
        Playbook(
            playbook_id="fnb_craving_reaction",
            name="Craving -> Food close-up -> Reaction -> Offer -> CTA",
            best_for=["coffee", "drink", "restaurant", "snack"],
            structure=["Craving", "Food close-up", "Reaction", "Offer", "CTA"],
            recommended_angles=["storytelling", "product_demo", "social_proof"],
            scene_formula=[
                "Show craving or hunger moment",
                "Show product close-up",
                "Show taste reaction",
                "Show offer and CTA",
            ],
        ),
        Playbook(
            playbook_id="fnb_product_reveal",
            name="Before hungry -> Product reveal -> Taste moment -> Order now",
            best_for=["delivery", "cafe", "quick treat"],
            structure=["Before hungry", "Product reveal", "Taste moment", "Order now"],
            recommended_angles=["curiosity", "product_demo"],
            scene_formula=[
                "Set the need state",
                "Reveal food or drink",
                "Show sip or bite",
                "Order CTA",
            ],
        ),
    ]
