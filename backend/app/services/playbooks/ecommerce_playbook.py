from app.models.schemas import Playbook


def get_ecommerce_playbooks() -> list[Playbook]:
    return [
        Playbook(
            playbook_id="ecommerce_problem_use_result",
            name="Problem -> Product use -> Before/after -> CTA",
            best_for=["physical product", "home item", "accessory"],
            structure=["Problem", "Product use", "Before/after", "CTA"],
            recommended_angles=["problem_solution", "product_demo"],
            scene_formula=[
                "Show everyday friction",
                "Use the product",
                "Show practical result",
                "CTA",
            ],
        ),
        Playbook(
            playbook_id="ecommerce_unboxing_demo",
            name="Unboxing -> Feature demo -> Social proof -> CTA",
            best_for=["fashion", "bag", "gadget", "giftable product"],
            structure=["Unboxing", "Feature demo", "Social proof", "CTA"],
            recommended_angles=["social_proof", "curiosity"],
            scene_formula=[
                "Unbox product",
                "Show key feature",
                "Show recommendation moment",
                "CTA",
            ],
        ),
    ]
