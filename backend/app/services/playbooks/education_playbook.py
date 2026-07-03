from app.models.schemas import Playbook


def get_education_playbooks() -> list[Playbook]:
    return [
        Playbook(
            playbook_id="education_pain_small_win",
            name="Learning pain -> App/course method -> Small win -> CTA",
            best_for=["learning app", "course", "language app"],
            structure=["Learning pain", "Method", "Small win", "CTA"],
            recommended_angles=["problem_solution", "product_demo", "storytelling"],
            scene_formula=[
                "Show learning pain",
                "Show practice method",
                "Show small learning win",
                "Sign up or install CTA",
            ],
        ),
        Playbook(
            playbook_id="education_simple_lesson",
            name="Before confusion -> Simple lesson -> Result -> Sign up",
            best_for=["beginner education", "language practice", "skill training"],
            structure=["Before confusion", "Simple lesson", "Result", "Sign up"],
            recommended_angles=["curiosity", "social_proof"],
            scene_formula=[
                "Show confusion",
                "Show simple lesson",
                "Show understood phrase or task",
                "CTA",
            ],
        ),
    ]
