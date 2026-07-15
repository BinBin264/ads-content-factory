import threading
import time
from contextlib import nullcontext
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from uuid import uuid4

from app.config import (
    IMAGE_GENERATION_CONCURRENCY,
    IMAGE_GENERATION_MAX_RETRIES,
    IMAGE_GENERATION_RETRY_BASE_SECONDS,
)
from app.models.schemas import ImageGenerationJob
from app.services.image_provider import ImageProviderError
from app.services.project_service import ProjectService


ACTIVE_JOB_STATUSES = {"queued", "running", "retrying"}


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class _JobState:
    id: str
    project_id: str
    job_type: str
    target_key: str
    scene_index: int | None = None
    slot_id: str | None = None
    asset_type: str | None = None
    model_id: str | None = None
    status: str = "queued"
    progress: int = 0
    phase: str = "Queued"
    attempt: int = 0
    max_attempts: int = IMAGE_GENERATION_MAX_RETRIES + 1
    error: str | None = None
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)


class ImageGenerationQueue:
    def __init__(
        self,
        project_service: ProjectService,
        *,
        concurrency: int = IMAGE_GENERATION_CONCURRENCY,
        max_attempts: int = IMAGE_GENERATION_MAX_RETRIES + 1,
        retry_base_seconds: float = IMAGE_GENERATION_RETRY_BASE_SECONDS,
    ) -> None:
        self.project_service = project_service
        self.max_attempts = max(1, max_attempts)
        self.retry_base_seconds = max(0.0, retry_base_seconds)
        self._jobs: dict[str, _JobState] = {}
        self._lock = threading.RLock()
        self._retry_serial_lock = threading.Lock()
        self._executor = ThreadPoolExecutor(max_workers=max(1, concurrency), thread_name_prefix="image-generation")

    def submit_reference_asset(
        self,
        project_id: str,
        asset_type: str,
        model_id: str,
    ) -> ImageGenerationJob:
        normalized_type = asset_type.strip().lower()
        if normalized_type not in {"character", "location"}:
            raise ValueError("asset_type must be character or location.")
        self.project_service.storage.get_project(project_id)
        target_key = f"reference:{normalized_type}"
        return self._submit(
            _JobState(
                id=f"image_job_{uuid4().hex[:12]}",
                project_id=project_id,
                job_type="reference_asset",
                target_key=target_key,
                asset_type=normalized_type,
                model_id=model_id,
                max_attempts=self.max_attempts,
            )
        )

    def submit_keyframe(
        self,
        project_id: str,
        scene_index: int,
        slot_id: str,
        model_id: str,
    ) -> ImageGenerationJob:
        project = self.project_service.storage.get_project(project_id)
        plan = self.project_service._require_plan(project)
        scene = self.project_service._find_scene(plan.scenes, scene_index)
        self.project_service._find_keyframe_slot(scene, slot_id)
        target_key = f"keyframe:{scene_index}:{slot_id}"
        return self._submit(
            _JobState(
                id=f"image_job_{uuid4().hex[:12]}",
                project_id=project_id,
                job_type="keyframe",
                target_key=target_key,
                scene_index=scene_index,
                slot_id=slot_id,
                model_id=model_id,
                max_attempts=self.max_attempts,
            )
        )

    def get(self, project_id: str, job_id: str) -> ImageGenerationJob:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None or job.project_id != project_id:
                raise ValueError(f"Image generation job '{job_id}' was not found.")
            return self._serialize(job)

    def list_for_project(self, project_id: str, *, active_only: bool = False) -> list[ImageGenerationJob]:
        with self._lock:
            jobs = [job for job in self._jobs.values() if job.project_id == project_id]
            if active_only:
                jobs = [job for job in jobs if job.status in ACTIVE_JOB_STATUSES]
            jobs.sort(key=lambda job: job.created_at)
            return [self._serialize(job) for job in jobs]

    def shutdown(self) -> None:
        self._executor.shutdown(wait=True, cancel_futures=True)

    def _submit(self, job: _JobState) -> ImageGenerationJob:
        with self._lock:
            for existing in self._jobs.values():
                if (
                    existing.project_id == job.project_id
                    and existing.target_key == job.target_key
                    and existing.status in ACTIVE_JOB_STATUSES
                ):
                    return self._serialize(existing)
            self._jobs[job.id] = job
        self._executor.submit(self._run, job.id)
        return self.get(job.project_id, job.id)

    def _run(self, job_id: str) -> None:
        for attempt in range(1, self.max_attempts + 1):
            retry_guard = self._retry_serial_lock if attempt > 1 else nullcontext()
            if attempt > 1:
                self._update(
                    job_id,
                    status="retrying",
                    phase=f"Retry {attempt - 1}/{self.max_attempts - 1}: waiting for provider slot",
                    attempt=attempt,
                )
            with retry_guard:
                if attempt > 1:
                    self._wait_for_other_running_jobs(job_id)
                self._update(job_id, status="running", phase="Preparing request", progress=5, attempt=attempt, error=None)
                try:
                    job = self._state(job_id)
                    progress_callback = lambda progress, phase: self._update(
                        job_id,
                        status="running",
                        progress=progress,
                        phase=phase,
                    )
                    if job.job_type == "reference_asset" and job.asset_type:
                        self.project_service.generate_reference_asset_image(
                            job.project_id,
                            job.asset_type,
                            model_id=job.model_id,
                            progress_callback=progress_callback,
                        )
                    elif job.job_type == "keyframe" and job.scene_index is not None and job.slot_id:
                        self.project_service.generate_keyframe_slot_image(
                            job.project_id,
                            job.scene_index,
                            job.slot_id,
                            model_id=job.model_id,
                            progress_callback=progress_callback,
                        )
                    else:
                        raise ValueError("Image generation job target is invalid.")
                    self._update(job_id, status="succeeded", phase="Complete", progress=100, error=None)
                    return
                except Exception as exc:  # noqa: BLE001 - job boundary must retain failure state
                    message = str(exc)
                    if attempt < self.max_attempts and self._is_retryable(exc):
                        delay = self.retry_base_seconds * (2 ** (attempt - 1))
                        self._update(
                            job_id,
                            status="retrying",
                            phase=f"Provider busy; retry {attempt}/{self.max_attempts - 1} in {delay:g}s",
                            error=message,
                        )
                        time.sleep(delay)
                        continue
                    self._update(job_id, status="failed", phase="Failed", error=message)
                    return

    def _state(self, job_id: str) -> _JobState:
        with self._lock:
            return self._jobs[job_id]

    def _update(self, job_id: str, **changes: object) -> None:
        with self._lock:
            current = self._jobs[job_id]
            if "progress" in changes:
                changes["progress"] = max(current.progress, min(100, int(changes["progress"])))
            changes["updated_at"] = _now()
            self._jobs[job_id] = replace(current, **changes)

    def _serialize(self, job: _JobState) -> ImageGenerationJob:
        payload = dict(job.__dict__)
        if job.status == "queued":
            ahead = sum(
                1
                for other in self._jobs.values()
                if other.id != job.id
                and other.status in ACTIVE_JOB_STATUSES
                and other.created_at <= job.created_at
            )
            payload["phase"] = f"Queued ({ahead} ahead)" if ahead else "Queued (next)"
        return ImageGenerationJob(**payload)

    def _wait_for_other_running_jobs(self, job_id: str) -> None:
        while True:
            with self._lock:
                has_other_running = any(
                    other.id != job_id and other.status == "running"
                    for other in self._jobs.values()
                )
            if not has_other_running:
                return
            time.sleep(0.1)

    def _is_retryable(self, exc: Exception) -> bool:
        if not isinstance(exc, ImageProviderError):
            return False
        message = str(exc).lower()
        return any(
            token in message
            for token in ("http 429", "http 503", "http 524", "timed out", "temporarily", "rate limit", "unavailable")
        )
