from pathlib import Path
from typing import Any

import pytest

from app.services.video_provider import ShopAIKeyVideoProvider, VideoReferenceInput, VideoTaskFailedError


def test_shopaikey_video_uses_one_keyframe_in_metadata_images(
    tmp_path: Path,
    monkeypatch,
) -> None:
    keyframe = tmp_path / "scene_01_keyframe_01.png"
    keyframe.write_bytes(b"keyframe")
    provider = ShopAIKeyVideoProvider(
        provider_name="shopaikey",
        api_key="test-key",
        base_url="https://api.shopaikey.com",
        model_id="veo3.1-pro",
        ratio="9:16",
        enhance_prompt=False,
        enable_upsample=True,
    )
    requests: list[dict[str, Any]] = []

    monkeypatch.setattr(provider, "_upload_image", lambda path, content_type: "https://cdn.example/keyframe.png")

    def fake_request_json(
        url: str,
        *,
        method: str,
        payload: dict[str, Any] | None = None,
        operation: str,
    ) -> dict[str, Any]:
        requests.append({"url": url, "method": method, "payload": payload, "operation": operation})
        if method == "POST":
            return {"code": "success", "data": {"task_id": "task-1", "status": "queued"}}
        return {
            "code": "success",
            "data": {
                "task_id": "task-1",
                "status": "SUCCESS",
                "result_url": "https://cdn.example/scene-01.mp4",
            },
        }

    monkeypatch.setattr(provider, "_request_json", fake_request_json)

    result = provider.generate_video(
        project_id="project-1",
        scene_index=1,
        prompt="Actor lifts the coin. Camera pushes in slowly.",
        references=[
            VideoReferenceInput(
                label=keyframe.name,
                role="keyframe",
                file_path=str(keyframe),
                content_type="image/png",
            )
        ],
        duration="8",
    )

    create_request = requests[0]
    assert create_request["url"] == "https://api.shopaikey.com/v1/video/generations"
    assert create_request["payload"] == {
        "model": "veo3.1-pro",
        "prompt": create_request["payload"]["prompt"],
        "metadata": {
            "images": ["https://cdn.example/keyframe.png"],
            "aspect_ratio": "9:16",
            "enhance_prompt": False,
            "enable_upsample": True,
        },
    }
    assert "Actor lifts the coin" in create_request["payload"]["prompt"]
    assert result.video_url is None
    assert result.job_id == "task-1"
    assert result.status == "QUEUED"
    assert result.progress == 0
    assert result.provider_name == "ShopAIKey"
    assert result.model_id == "veo3.1-pro"
    assert result.mode == "first_frame"
    assert result.references[0].role == "keyframe"

    completed = provider.poll_video(
        project_id="project-1",
        job_id=result.job_id,
        references=result.references,
        duration=result.duration,
        model_id=result.model_id,
    )

    assert completed.video_url == "https://cdn.example/scene-01.mp4"
    assert completed.status == "VIDEO_READY"
    assert completed.progress == 100


def test_shopaikey_video_reuses_image_provider_key_by_default() -> None:
    provider = ShopAIKeyVideoProvider(provider_name="shopaikey", api_key="shared-key")

    assert provider.is_configured is True
    assert provider.reference_limit == 1


def test_shopaikey_terminal_failure_uses_typed_error() -> None:
    provider = ShopAIKeyVideoProvider(provider_name="shopaikey", api_key="shared-key")

    with pytest.raises(VideoTaskFailedError, match="task timeout"):
        provider._raise_provider_error(
            {
                "code": "success",
                "data": {
                    "status": "FAILURE",
                    "fail_reason": "task timeout",
                },
            }
        )


def test_veo_fast_components_forces_landscape_components_profile() -> None:
    provider = ShopAIKeyVideoProvider(
        provider_name="shopaikey",
        api_key="shared-key",
        ratio="9:16",
        enable_upsample=True,
    )

    profile = provider.get_model_profile(model_id="veo3.1-fast-components", duration="8")

    assert profile.model_id == "veo3.1-fast-components"
    assert profile.family == "veo"
    assert profile.ratio == "16:9"
    assert profile.mode == "components"
    assert profile.duration == "8"


def test_grok_video_uses_grok_metadata_fields(
    tmp_path: Path,
    monkeypatch,
) -> None:
    keyframe = tmp_path / "scene_02_keyframe_01.png"
    keyframe.write_bytes(b"keyframe")
    provider = ShopAIKeyVideoProvider(
        provider_name="shopaikey",
        api_key="test-key",
        base_url="https://api.shopaikey.com",
    )
    requests: list[dict[str, Any]] = []
    monkeypatch.setattr(provider, "_upload_image", lambda path, content_type: "https://cdn.example/keyframe.png")

    def fake_request_json(
        url: str,
        *,
        method: str,
        payload: dict[str, Any] | None = None,
        operation: str,
    ) -> dict[str, Any]:
        requests.append({"url": url, "method": method, "payload": payload, "operation": operation})
        if method == "POST":
            return {"code": "success", "data": {"task_id": "grok-task", "status": "queued"}}
        return {
            "code": "success",
            "data": {
                "task_id": "grok-task",
                "status": "SUCCESS",
                "result_url": "https://cdn.example/grok-scene.mp4",
            },
        }

    monkeypatch.setattr(provider, "_request_json", fake_request_json)

    result = provider.generate_video(
        project_id="project-1",
        scene_index=2,
        prompt="The actor opens the app.",
        references=[VideoReferenceInput(label=keyframe.name, role="keyframe", file_path=str(keyframe))],
        duration="8",
        model_id="grok-video-3",
    )

    assert requests[0]["payload"] == {
        "model": "grok-video-3",
        "prompt": requests[0]["payload"]["prompt"],
        "metadata": {
            "images": ["https://cdn.example/keyframe.png"],
            "duration": 8,
            "ratio": "2:3",
            "resolution": "1080P",
        },
    }
    assert result.model_id == "grok-video-3"
    assert result.ratio == "2:3"
    assert result.mode == "image_to_video"
    assert result.resolution == "1080P"


def test_grok_10s_profile_uses_fixed_duration() -> None:
    provider = ShopAIKeyVideoProvider(provider_name="shopaikey", api_key="shared-key")

    profile = provider.get_model_profile(model_id="grok-video-3-10s", duration="4")

    assert profile.duration == "10"


def test_shopaikey_progress_uses_provider_response() -> None:
    provider = ShopAIKeyVideoProvider(provider_name="shopaikey", api_key="shared-key")

    assert provider._extract_progress({"data": {"status": "processing", "progress": "50%"}}) == 50
    assert provider._extract_progress({"data": {"status": "SUCCESS", "progress": "100%"}}) == 100


def test_shopaikey_poll_returns_after_one_status_request(monkeypatch) -> None:
    provider = ShopAIKeyVideoProvider(provider_name="shopaikey", api_key="shared-key")
    calls = 0

    def fake_status(job_id: str) -> dict[str, Any]:
        nonlocal calls
        calls += 1
        return {"code": "success", "data": {"task_id": job_id, "status": "processing", "progress": "50%"}}

    monkeypatch.setattr(provider, "_get_video_status", fake_status)

    result = provider.poll_video(project_id="project-1", job_id="task-1", model_id="veo3.1-pro", duration="8")

    assert calls == 1
    assert result.status == "PROCESSING"
    assert result.progress == 50
