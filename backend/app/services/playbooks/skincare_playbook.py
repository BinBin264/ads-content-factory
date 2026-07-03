from app.models.schemas import Playbook


def get_skincare_playbooks() -> list[Playbook]:
    return [
        Playbook(
            playbook_id="skincare_routine_expectation",
            name="Pain point -> Routine demo -> Texture/application -> Realistic expectation -> CTA",
            best_for=["serum", "cream", "skincare routine"],
            structure=["Pain point", "Routine demo", "Texture/application", "Realistic expectation", "CTA"],
            recommended_angles=["problem_solution", "product_demo", "storytelling"],
            scene_formula=[
                "Show skin concern or routine hook",
                "Show product texture or application",
                "Show how it fits into routine",
                "Show realistic benefit and CTA",
            ],
        ),
        Playbook(
            playbook_id="skincare_closeup_how_to",
            name="Problem skin -> Product close-up -> How to use -> Benefit -> CTA",
            best_for=["acne-prone skin", "texture concern", "daily skincare"],
            structure=["Problem skin", "Product close-up", "How to use", "Benefit", "CTA"],
            recommended_angles=["product_demo", "curiosity"],
            scene_formula=[
                "Name the skin concern",
                "Show packaging and texture",
                "Show application step",
                "Set a safe expectation",
            ],
        ),
    ]
