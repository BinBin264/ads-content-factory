import threading
import time
from types import SimpleNamespace

from app.services.image_generation_queue import ImageGenerationQueue
from app.services.image_provider import ImageProviderError


class FakeStorage:
    def get_project(self, project_id: str):
        return SimpleNamespace(id=project_id, creative_plan=SimpleNamespace(scenes=[]))


class FakeProjectService:
    def __init__(
        self,
        *,
        fail_once: bool = False,
        failures_before_success: int = 0,
        failure_message: str = "Image provider HTTP 429: rate limit",
    ) -> None:
        self.storage = FakeStorage()
        self.failures_before_success = max(failures_before_success, 1 if fail_once else 0)
        self.failure_message = failure_message
        self.calls = 0
        self.started = threading.Event()
        self.release = threading.Event()
        self.models = []

    def generate_reference_asset_image(self, project_id, asset_type, *, model_id=None, progress_callback=None):
        self.calls += 1
        self.models.append(model_id)
        if self.calls <= self.failures_before_success:
            raise ImageProviderError(self.failure_message)
        if asset_type == "character":
            self.started.set()
            self.release.wait(timeout=2)
        if progress_callback:
            progress_callback(50, "Provider generating image")
            progress_callback(98, "Updating project")
        return SimpleNamespace(id=project_id)

    def _require_plan(self, project):
        return project.creative_plan

    def _find_scene(self, scenes, scene_index):
        return {"sceneIndex": scene_index, "keyframePrompts": [{"id": "kf_main"}]}

    def _find_keyframe_slot(self, scene, slot_id):
        return scene["keyframePrompts"][0]


def wait_for_terminal(queue: ImageGenerationQueue, project_id: str, job_id: str):
    deadline = time.time() + 3
    while time.time() < deadline:
        job = queue.get(project_id, job_id)
        if job.status in {"succeeded", "failed"}:
            return job
        time.sleep(0.01)
    raise AssertionError("Image generation job did not finish")


def test_second_image_waits_in_queue_when_worker_is_busy() -> None:
    service = FakeProjectService()
    queue = ImageGenerationQueue(service, concurrency=1, max_attempts=1, retry_base_seconds=0)
    try:
        first = queue.submit_reference_asset("project_1", "character", "nano-banana-pro")
        assert service.started.wait(timeout=1)
        second = queue.submit_reference_asset("project_1", "location", "nano-banana-2")

        assert queue.get("project_1", second.id).status == "queued"
        service.release.set()

        assert wait_for_terminal(queue, "project_1", first.id).status == "succeeded"
        assert wait_for_terminal(queue, "project_1", second.id).status == "succeeded"
        assert service.models[0] == "nano-banana-pro"
    finally:
        service.release.set()
        queue.shutdown()


def test_rate_limited_image_job_retries_automatically() -> None:
    service = FakeProjectService(fail_once=True)
    service.release.set()
    queue = ImageGenerationQueue(service, concurrency=1, max_attempts=2, retry_base_seconds=0.01)
    try:
        job = queue.submit_reference_asset("project_1", "character", "nano-banana-2")
        completed = wait_for_terminal(queue, "project_1", job.id)

        assert completed.status == "succeeded"
        assert completed.attempt == 2
        assert completed.progress == 100
        assert service.calls == 2
    finally:
        queue.shutdown()


def test_http_524_image_job_retries_three_times_after_initial_attempt() -> None:
    service = FakeProjectService(
        failures_before_success=4,
        failure_message="Image provider GPT image generation HTTP 524: error code: 524",
    )
    service.release.set()
    queue = ImageGenerationQueue(service, concurrency=1, max_attempts=4, retry_base_seconds=0)
    try:
        job = queue.submit_reference_asset("project_1", "character", "gpt-image-2-all")
        completed = wait_for_terminal(queue, "project_1", job.id)

        assert completed.status == "failed"
        assert completed.attempt == 4
        assert completed.max_attempts == 4
        assert service.calls == 4
        assert "HTTP 524" in (completed.error or "")
    finally:
        queue.shutdown()
