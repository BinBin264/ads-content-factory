from app.models.schemas import Playbook


def get_app_playbooks() -> list[Playbook]:
    return [
        Playbook(
            playbook_id="mobile_app_problem_demo_result",
            name="Problem -> App Demo -> Result -> CTA",
            best_for=["mobile app", "utility tool", "SaaS", "scanner app"],
            structure=["Problem", "App demo", "Result", "CTA"],
            recommended_angles=["problem_solution", "product_demo", "storytelling"],
            scene_formula=[
                "User shows the problem or object",
                "Open the app",
                "Use the key feature",
                "Show result and CTA",
            ],
        ),
        Playbook(
            playbook_id="mobile_app_curiosity_reveal",
            name="Curiosity -> Use App -> Reveal Result -> CTA",
            best_for=["scanner", "discovery app", "utility app"],
            structure=["Curiosity", "Use app", "Reveal result", "CTA"],
            recommended_angles=["curiosity", "storytelling"],
            scene_formula=[
                "Show surprising object or situation",
                "Open app and start action",
                "Reveal useful app result",
                "Prompt viewer to try it",
            ],
        ),
        Playbook(
            playbook_id="mobile_app_tutorial",
            name="Tutorial -> Step 1 -> Step 2 -> Benefit -> CTA",
            best_for=["app onboarding", "feature education"],
            structure=["Tutorial", "Step 1", "Step 2", "Benefit", "CTA"],
            recommended_angles=["product_demo", "social_proof"],
            scene_formula=[
                "Announce quick tutorial",
                "Show first app step",
                "Show second app step",
                "Explain practical benefit",
            ],
        ),
    ]
