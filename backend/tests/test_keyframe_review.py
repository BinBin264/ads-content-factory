from pathlib import Path

import pytest

from app.models.schemas import (
    CreativePlan,
    Project,
    ReviewKeyframeRequest,
    UpdateKeyframePromptSlotRequest,
    UpdateSceneRequest,
)
from app.services.project_service import ProjectService
from app.services.storage_service import JsonProjectStorage


def build_reviewable_project() -> Project:
    project = Project(product_name="Review gate test")
    plan = CreativePlan(
        productAnalysis={"coreBenefit": "Test", "productLockPrompt": "Keep the product unchanged."},
        primaryCharacter={"description": "One actor", "consistencyPrompt": "Same identity."},
        primaryLocation={"description": "One room", "consistencyPrompt": "Same room."},
        scenes=[
            {
                "sceneIndex": 1,
                "title": "Opening",
                "openingState": "The actor stands still before reaching for the product.",
                "sceneGoal": "Introduce the product",
                "visualAction": "The actor reaches for the product.",
                "characterAction": "One actor reaches with the right hand.",
                "productMoment": "The product remains unchanged.",
                "camera": {"shot": "medium shot", "movement": "static", "composition": "actor and product readable"},
                "voiceLines": [],
                "keyframePrompts": [
                    {
                        "id": "kf_main",
                        "prompt": "One actor standing still beside the product.",
                        "productReferenceIds": [],
                        "selectedCandidateId": "candidate_1",
                        "selectedImageUrl": "/uploads/test/keyframe.png",
                        "qualityGate": {"status": "review_required"},
                    }
                ],
                "negativeRules": ["no duplicate actor"],
            }
        ],
    )
    project.creative_plan = plan
    return project


def test_accept_keyframe_is_bound_to_selected_candidate(tmp_path: Path) -> None:
    storage = JsonProjectStorage(tmp_path / "projects.json")
    project = storage.save_project(build_reviewable_project())
    service = ProjectService(storage=storage)

    reviewed = service.review_keyframe(
        project.id,
        1,
        "kf_main",
        ReviewKeyframeRequest(verdict="accept"),
    )
    slot = reviewed.creative_plan.scenes[0]["keyframePrompts"][0]

    assert slot["qualityGate"]["status"] == "accepted"
    assert slot["qualityGate"]["acceptedCandidateId"] == "candidate_1"
    assert reviewed.creative_plan.scenes[0]["status"] == "KEYFRAME_ACCEPTED"


def test_reject_keyframe_does_not_mark_it_ready_for_video(tmp_path: Path) -> None:
    storage = JsonProjectStorage(tmp_path / "projects.json")
    project = storage.save_project(build_reviewable_project())
    service = ProjectService(storage=storage)

    reviewed = service.review_keyframe(
        project.id,
        1,
        "kf_main",
        ReviewKeyframeRequest(verdict="reject", defects=["duplicate_actor", "bad_hands"]),
    )
    slot = reviewed.creative_plan.scenes[0]["keyframePrompts"][0]

    assert slot["qualityGate"]["status"] == "rejected"
    assert slot["qualityGate"]["acceptedCandidateId"] is None
    assert slot["qualityGate"]["defects"] == ["duplicate_actor", "bad_hands"]
    assert reviewed.creative_plan.scenes[0]["finalVideoPromptStale"] is True


def test_review_requires_a_selected_image(tmp_path: Path) -> None:
    project = build_reviewable_project()
    slot = project.creative_plan.scenes[0]["keyframePrompts"][0]
    slot["selectedCandidateId"] = None
    slot["selectedImageUrl"] = None
    storage = JsonProjectStorage(tmp_path / "projects.json")
    storage.save_project(project)
    service = ProjectService(storage=storage)

    with pytest.raises(ValueError, match="Generate or upload"):
        service.review_keyframe(
            project.id,
            1,
            "kf_main",
            ReviewKeyframeRequest(verdict="accept"),
        )


def test_accepted_keyframe_blocks_prompt_edits_and_regeneration(tmp_path: Path) -> None:
    storage = JsonProjectStorage(tmp_path / "projects.json")
    project = storage.save_project(build_reviewable_project())
    service = ProjectService(storage=storage)
    service.review_keyframe(project.id, 1, "kf_main", ReviewKeyframeRequest(verdict="accept"))

    with pytest.raises(ValueError, match="Keyframe is accepted"):
        service.update_keyframe_prompt_slot(
            project.id,
            1,
            "kf_main",
            UpdateKeyframePromptSlotRequest(prompt="A different opening pose."),
        )
    with pytest.raises(ValueError, match="Keyframe is accepted"):
        service.generate_keyframe_slot_image(
            project.id,
            1,
            "kf_main",
            model_id="nano-banana-2",
        )

    stored = storage.get_project(project.id)
    slot = stored.creative_plan.scenes[0]["keyframePrompts"][0]
    assert slot["prompt"] != "A different opening pose."
    assert slot["qualityGate"]["status"] == "accepted"
    assert slot["qualityGate"]["acceptedCandidateId"] == slot["selectedCandidateId"]


def test_rejecting_keyframe_unlocks_prompt_editing(tmp_path: Path) -> None:
    storage = JsonProjectStorage(tmp_path / "projects.json")
    project = storage.save_project(build_reviewable_project())
    service = ProjectService(storage=storage)
    service.review_keyframe(project.id, 1, "kf_main", ReviewKeyframeRequest(verdict="accept"))
    service.review_keyframe(project.id, 1, "kf_main", ReviewKeyframeRequest(verdict="reject"))

    updated = service.update_keyframe_prompt_slot(
        project.id,
        1,
        "kf_main",
        UpdateKeyframePromptSlotRequest(prompt="A different opening pose."),
    )
    slot = updated.creative_plan.scenes[0]["keyframePrompts"][0]

    assert slot["prompt"] == "A different opening pose."
    assert slot["stale"] is True
    assert slot["qualityGate"]["status"] == "review_required"


def test_editing_scene_invalidates_previous_keyframe_acceptance(tmp_path: Path) -> None:
    storage = JsonProjectStorage(tmp_path / "projects.json")
    project = storage.save_project(build_reviewable_project())
    service = ProjectService(storage=storage)
    service.review_keyframe(project.id, 1, "kf_main", ReviewKeyframeRequest(verdict="accept"))

    updated = service.update_scene(
        project.id,
        1,
        UpdateSceneRequest(visualAction="The actor places the product back on the table."),
    )
    slot = updated.creative_plan.scenes[0]["keyframePrompts"][0]

    assert slot["stale"] is True
    assert slot["qualityGate"]["status"] == "review_required"
    assert slot["qualityGate"]["acceptedCandidateId"] is None


def test_scene_generation_is_not_gated_by_previous_clip_review(tmp_path: Path) -> None:
    project = build_reviewable_project()
    first_scene = project.creative_plan.scenes[0]
    second_scene = {
        **first_scene,
        "sceneIndex": 2,
        "sceneId": "scene_02",
        "clipId": "clip_02",
        "title": "Second scene",
        "videoUrl": None,
        "videoJobId": None,
        "takeReview": None,
        "keyframePrompts": [
            {
                **first_scene["keyframePrompts"][0],
                "selectedCandidateId": "candidate_2",
                "qualityGate": {"status": "accepted", "acceptedCandidateId": "candidate_2"},
            }
        ],
    }
    project.creative_plan.scenes.append(second_scene)
    storage = JsonProjectStorage(tmp_path / "projects.json")
    project = storage.save_project(project)
    stored = storage.get_project(project.id)

    assert stored.creative_plan.scenes[0].get("takeReview") is None
    assert stored.creative_plan.scenes[1]["keyframePrompts"][0]["qualityGate"]["status"] == "accepted"


def test_regenerate_clip_reset_preserves_phase_two_keyframe(tmp_path: Path) -> None:
    project = build_reviewable_project()
    scene = project.creative_plan.scenes[0]
    scene["videoUrl"] = "https://cdn.example.com/scene-01.mp4"
    scene["videoJobId"] = "task_old"
    scene["videoProgress"] = 100
    scene["takeReview"] = {"verdict": "keep", "accepted": True}
    selected_image = scene["keyframePrompts"][0]["selectedImageUrl"]
    storage = JsonProjectStorage(tmp_path / "projects.json")
    project = storage.save_project(project)
    service = ProjectService(storage=storage)

    service._reset_scene_video(project, project.creative_plan.scenes[0])
    reset_scene = project.creative_plan.scenes[0]

    assert reset_scene["videoUrl"] is None
    assert reset_scene["videoJobId"] is None
    assert reset_scene["takeReview"] is None
    assert reset_scene["keyframePrompts"][0]["selectedImageUrl"] == selected_image


def test_regenerate_clip_service_always_forces_replacement(tmp_path: Path, monkeypatch) -> None:
    storage = JsonProjectStorage(tmp_path / "projects.json")
    project = storage.save_project(build_reviewable_project())
    service = ProjectService(storage=storage)
    calls: list[dict] = []

    def fake_generate(
        project_id: str,
        scene_index: int,
        model_id: str | None = None,
        *,
        force: bool = False,
    ) -> Project:
        calls.append(
            {
                "project_id": project_id,
                "scene_index": scene_index,
                "model_id": model_id,
                "force": force,
            }
        )
        return storage.get_project(project_id)

    monkeypatch.setattr(service, "generate_scene_video", fake_generate)

    service.regenerate_scene_video(project.id, 1, "veo3.1-pro")

    assert calls == [
        {
            "project_id": project.id,
            "scene_index": 1,
            "model_id": "veo3.1-pro",
            "force": True,
        }
    ]
