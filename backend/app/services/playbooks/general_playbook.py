from app.models.schemas import Playbook


def get_general_playbooks() -> list[Playbook]:
    return [
        Playbook(
            playbook_id="general_ugc_demo",
            name="Hook -> Problem -> Product -> Result -> CTA",
            best_for=["general product", "unknown category", "UGC demo"],
            structure=["Hook", "Problem", "Product", "Result", "CTA"],
            recommended_angles=["storytelling", "product_demo", "problem_solution", "curiosity", "social_proof"],
            scene_formula=[
                "Hook viewer",
                "Set problem",
                "Demo product",
                "Result and CTA",
            ],
        )
    ]
