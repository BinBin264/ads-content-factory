import unittest

import pytest

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

    def test_accepting_clip_does_not_rewrite_next_scene(self) -> None:
        project, plan = build_plan()
        orchestrator = ProductionOrchestrator()
        prepared = orchestrator.prepare_plan(project, plan)
        next_prompt = prepared.scenes[1]["finalVideoPrompt"]
        next_start = prepared.scenes[1]["shotContract"]["plannedStartState"]
        orchestrator.review_take(
            prepared,
            prepared.scenes[0],
            {"verdict": "keep"},
        )

        self.assertTrue(prepared.scenes[0]["takeReview"]["accepted"])
        self.assertEqual(prepared.scenes[1]["finalVideoPrompt"], next_prompt)
        self.assertEqual(prepared.scenes[1]["shotContract"]["plannedStartState"], next_start)

    def test_accepting_clip_requires_no_manual_end_state(self) -> None:
        project, plan = build_plan()
        orchestrator = ProductionOrchestrator()
        prepared = orchestrator.prepare_plan(project, plan)

        orchestrator.review_take(prepared, prepared.scenes[0], {"verdict": "keep"})

        self.assertEqual(prepared.scenes[0]["status"], "ACCEPTED")

    def test_rejected_review_verdicts_are_not_supported(self) -> None:
        project, plan = build_plan()
        orchestrator = ProductionOrchestrator()
        prepared = orchestrator.prepare_plan(project, plan)

        with pytest.raises(ValueError, match="Only keep"):
            orchestrator.review_take(prepared, prepared.scenes[0], {"verdict": "reject"})

    def test_long_dialogue_is_moved_to_post_and_not_sent_to_video_model(self) -> None:
        project, plan = build_plan()
        scene = plan.scenes[0]
        scene["durationSec"] = 4
        scene["voiceLines"] = [
            {
                "speaker": "Primary actor",
                "timing": "0-4s",
                "emotion": "reflective",
                "delivery": "natural Spanish",
                "line": "En el mercado siempre hay tesoros pero no quiero que nadie vuelva a enganarme hoy.",
            }
        ]

        prepared = ProductionOrchestrator().prepare_plan(project, plan)
        prepared_scene = prepared.scenes[0]
        prompt = prepared_scene["finalVideoPrompt"]

        self.assertEqual(prepared_scene["voiceLines"][0]["generationMode"], "post_voiceover")
        self.assertEqual(prepared_scene["shotContract"]["audioPhase"], "post_voiceover")
        self.assertIn("Generate no speech or lip-sync", prompt)
        self.assertNotIn("En el mercado", prompt)

    def test_keyframe_contract_is_opening_state_before_action(self) -> None:
        project, plan = build_plan()
        plan.scenes[0]["openingState"] = "The actor's empty right hand rests beside the coin."

        prepared = ProductionOrchestrator().prepare_plan(project, plan)
        scene = prepared.scenes[0]

        self.assertEqual(scene["shotContract"]["keyframeRole"], "opening_state_before_action")
        self.assertEqual(scene["keyframePrompts"][0]["keyframeRole"], "frame_0_before_action")
        self.assertIn("empty right hand", scene["shotContract"]["plannedStartState"]["visibleOpening"])

    def test_product_closeup_routes_only_the_product_reference(self) -> None:
        project, plan = build_plan()
        plan.productReferences = [
            {
                "id": "home_screen",
                "referenceLabel": "product_ref_01_home",
                "lockPrompt": "Keep the home screen pixels unchanged.",
            }
        ]
        scene = plan.scenes[1]
        scene["camera"]["shot"] = "phone screen close-up"
        scene["camera"]["composition"] = "UI readable"
        scene["keyframePrompts"][0]["productReferenceIds"] = ["home_screen"]

        prepared = ProductionOrchestrator().prepare_plan(project, plan)
        tags = [
            binding["tag"]
            for binding in prepared.scenes[1]["keyframePrompts"][0]["referenceBindings"]
        ]

        self.assertEqual(tags, ["@product_ref_01_home"])

    def test_keyframe_acceptance_is_tied_to_selected_candidate(self) -> None:
        project, plan = build_plan()
        slot = plan.scenes[0]["keyframePrompts"][0]
        slot["selectedCandidateId"] = "candidate_7"
        slot["selectedImageUrl"] = "/uploads/keyframe.png"
        slot["qualityGate"] = {"status": "accepted", "acceptedCandidateId": "candidate_7"}

        prepared = ProductionOrchestrator().prepare_plan(project, plan)
        prepared_slot = prepared.scenes[0]["keyframePrompts"][0]
        self.assertEqual(prepared_slot["qualityGate"]["status"], "accepted")

        prepared_slot["selectedCandidateId"] = "candidate_8"
        ProductionOrchestrator().refresh_scene(prepared, prepared.scenes[0], compile_prompt=True)
        self.assertEqual(prepared_slot["qualityGate"]["status"], "review_required")
        self.assertIsNone(prepared_slot["qualityGate"]["acceptedCandidateId"])


if __name__ == "__main__":
    unittest.main()
