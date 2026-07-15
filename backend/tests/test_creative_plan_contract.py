from app.models.schemas import NormalizedBrief, Project, VisionAnalysis
from app.services.creative_plan import CreativePlanService


def test_scene_coercion_separates_opening_state_and_long_voiceover() -> None:
    service = CreativePlanService(llm_provider=object())
    scenes = service._coerce_scene_clips(
        [
            {
                "title": "Open the box",
                "durationSec": 4,
                "sceneGoal": "Create curiosity",
                "openingState": "The closed box rests on the table and the actor's hands are relaxed beside it.",
                "visualAction": "The actor opens the box and stops when the coin is visible.",
                "voiceLines": [
                    {
                        "speaker": "Narrator",
                        "line": "This exact narration is deliberately too long to fit naturally inside four seconds.",
                    }
                ],
                "camera": {"shot": "medium shot", "composition": "box and hands readable"},
                "keyframePrompts": [],
            },
            {
                "title": "Inspect the coin",
                "durationSec": 4,
                "sceneGoal": "Show the discovery",
                "visualAction": "The actor lifts the coin once.",
                "voiceLines": [],
                "camera": {"shot": "close-up", "composition": "coin readable"},
                "keyframePrompts": [],
            },
        ],
        [],
    )

    assert scenes[0]["voiceLines"][0]["generationMode"] == "post_voiceover"
    assert "closed box" in scenes[0]["openingState"]
    assert scenes[1]["openingState"] == scenes[0]["visualAction"]
    assert scenes[0]["keyframePrompts"][0]["label"] == "Opening keyframe"
    assert "opens the box" not in scenes[0]["keyframePrompts"][0]["prompt"]


def test_planner_prompt_contains_source_carries_state_rules() -> None:
    service = CreativePlanService(llm_provider=object())
    project = Project(product_name="Coin Scanner", product_description="Scan old coins.")
    brief = NormalizedBrief(
        product_name="Coin Scanner",
        category="mobile app",
        product_type="mobile_app",
        short_description="Scan old coins.",
        target_audience=["collectors"],
        main_problem="Unknown coin",
        main_benefit="Reference information",
        emotional_triggers=[],
        functional_benefits=[],
        proof_elements=[],
        safe_claims=[],
        claims_to_avoid=[],
        recommended_visual_style="realistic",
        recommended_ad_formats=["tiktok"],
    )
    prompt = service._build_prompt(project, brief, VisionAnalysis())

    assert "frame 0 immediately BEFORE visualAction starts" in prompt
    assert "Reference allocation is a fidelity budget" in prompt
    assert "post_voiceover" in prompt
    assert "Do not re-describe static details already visible" in prompt
