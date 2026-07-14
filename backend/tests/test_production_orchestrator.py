import unittest

from app.models.schemas import CreativePlan, Project
from app.services.production_orchestrator import ProductionOrchestrator


def build_plan() -> tuple[Project, CreativePlan]:
    project = Project(
        product_name="Coin Scanner",
        product_description="An app that identifies old coins.",
        brief="A person finds a coin, scans it, then reacts to the result.",
    )
    plan = CreativePlan(
        productAnalysis={"coreBenefit": "Identify old coins", "productLockPrompt": "Keep the app UI unchanged."},
        primaryCharacter={"description": "One adult actor", "consistencyPrompt": "Keep the same face and outfit."},
        primaryLocation={"description": "One home table", "consistencyPrompt": "Keep the same table layout and light direction."},
        scenes=[
            {
                "sceneIndex": 1,
                "title": "Find the coin",
                "sceneGoal": "Create curiosity",
                "visualAction": "The actor picks up one old coin.",
                "characterAction": "The actor studies it with a restrained curious look.",
                "productMoment": "The physical coin is visible.",
                "camera": {"shot": "medium shot", "movement": "slow push-in", "composition": "actor and coin readable"},
                "voiceLines": [
                    {
                        "speaker": "Primary actor",
                        "timing": "0-6s",
                        "emotion": "reflective",
                        "delivery": "quiet and cautious",
                        "line": "What is this coin?",
                    }
                ],
                "ambientAudio": "quiet room tone and coin handling",
                "onScreenText": "",
                "keyframePrompts": [{"id": "kf_main", "prompt": "Actor picks up the coin", "productReferenceIds": []}],
                "finalVideoPrompt": "Legacy generated prompt",
                "negativeRules": ["no deformed hands"],
                "videoUrl": "/uploads/scene_01.mp4",
            },
            {
                "sceneIndex": 2,
                "title": "Scan the coin",
                "sceneGoal": "Show product proof",
                "visualAction": "The actor scans the coin in the app.",
                "characterAction": "The actor keeps the phone steady and watches the screen.",
                "productMoment": "The scan screen is visible.",
                "camera": {"shot": "phone close-up", "movement": "static", "composition": "screen readable"},
                "voiceLines": [],
                "ambientAudio": "one tap sound",
                "onScreenText": "Scan it",
                "keyframePrompts": [{"id": "kf_main", "prompt": "Phone scan screen", "productReferenceIds": []}],
                "finalVideoPrompt": "Legacy generated prompt",
                "negativeRules": ["no UI redesign"],
            },
        ],
    )
    return project, plan


class ProductionOrchestratorTests(unittest.TestCase):
    def test_compiler_keeps_provider_parameters_out_of_prompt(self) -> None:
        project, plan = build_plan()
        prepared = ProductionOrchestrator().prepare_plan(project, plan)

        prompt = prepared.scenes[0]["finalVideoPrompt"]
        self.assertNotIn("9:16", prompt)
        self.assertNotRegex(prompt.lower(), r"create (?:a|one) (?:4|6|8|10)[- ]second")
        self.assertIn("Directing intent:", prompt)
        self.assertIn("Emotional progression:", prompt)
        self.assertIn("Visual fidelity priority:", prompt)
        self.assertIn("0-8s / Primary actor / reflective / quiet and cautious: <What is this coin?>", prompt)
        self.assertEqual(prepared.scenes[0]["promptQuality"]["status"], "ready")
        self.assertEqual(len(prepared.scenes[0]["shotContract"]["thisClipOnly"]), 1)

    def test_only_accepted_take_updates_next_scene_handoff(self) -> None:
        project, plan = build_plan()
        orchestrator = ProductionOrchestrator()
        prepared = orchestrator.prepare_plan(project, plan)
        orchestrator.review_take(
            prepared,
            prepared.scenes[0],
            {
                "verdict": "keep",
                "observed_end_state": {"actorPose": "phone now in right hand", "coinPosition": "left palm"},
                "completed_beats": ["Find the coin"],
                "observation_confidence": "high",
            },
        )

        handoff = prepared.scenes[1]["shotContract"]["observedHandoff"]
        self.assertEqual(handoff["actorPose"], "phone now in right hand")
        self.assertTrue(prepared.scenes[0]["takeReview"]["canonAccepted"])
        self.assertEqual(prepared.sequenceState["canonRevision"], 2)


if __name__ == "__main__":
    unittest.main()
