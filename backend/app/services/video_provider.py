import base64
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.config import (
    VIDEO_MODEL_DURATION,
    VIDEO_MODEL_ID,
    VIDEO_MODEL_MODE,
    VIDEO_MODEL_RATIO,
    VIDEO_MODEL_RESOLUTION,
    VIDEO_TRANSLATE_TO_EN,
    VIDEO_POLL_INTERVAL_SECONDS,
    VIDEO_POLL_TIMEOUT_SECONDS,
    VIDEO_PROVIDER_API_KEY,
    VIDEO_PROVIDER_BASE_URL,
    VIDEO_PROVIDER_DOMAIN,
    VIDEO_PROVIDER_NAME,
    VIDEO_REFERENCE_LIMIT,
)


class VideoProviderError(Exception):
    pass


@dataclass
class VideoReferenceInput:
    label: str
    role: str
    url: str | None = None
    file_path: str | None = None
    content_type: str | None = None


@dataclass
class VideoReferenceUpload:
    label: str
    role: str
    url: str
    source: str | None = None


@dataclass
class GeneratedVideo:
    video_url: str | None
    job_id: str | None
    status: str
    message: str | None
    raw_response: dict[str, Any]
    references: list[VideoReferenceUpload]
    provider_name: str
    model_id: str
    ratio: str
    duration: str
    mode: str
    resolution: str


class GommoOmniVideoProvider:
    """79AI/Gommo video provider for VEO Omni Flash reference ingredients."""

    def __init__(
        self,
        *,
        provider_name: str = VIDEO_PROVIDER_NAME,
        api_key: str = VIDEO_PROVIDER_API_KEY,
        base_url: str = VIDEO_PROVIDER_BASE_URL,
        domain: str = VIDEO_PROVIDER_DOMAIN,
        model_id: str = VIDEO_MODEL_ID,
        mode: str = VIDEO_MODEL_MODE,
        ratio: str = VIDEO_MODEL_RATIO,
        duration: str = VIDEO_MODEL_DURATION,
        resolution: str = VIDEO_MODEL_RESOLUTION,
        translate_to_en: str = VIDEO_TRANSLATE_TO_EN,
        reference_limit: int = VIDEO_REFERENCE_LIMIT,
        poll_interval_seconds: float = VIDEO_POLL_INTERVAL_SECONDS,
        poll_timeout_seconds: float = VIDEO_POLL_TIMEOUT_SECONDS,
        request_timeout_seconds: int = 90,
    ) -> None:
        self.provider_name = provider_name.strip()
        self.api_key = api_key.strip()
        self.base_url = base_url.rstrip("/")
        self.domain = domain.strip()
        self.model_id = model_id.strip() or "veo_omni"
        self.mode = mode.strip() or "flash"
        self.ratio = ratio.strip() or "9:16"
        self.duration = str(duration).strip() or "4"
        self.resolution = resolution.strip() or "720p"
        self.translate_to_en = str(translate_to_en).strip().lower() or "false"
        self.reference_limit = max(1, reference_limit)
        self.poll_interval_seconds = max(1.0, poll_interval_seconds)
        self.poll_timeout_seconds = max(1.0, poll_timeout_seconds)
        self.request_timeout_seconds = request_timeout_seconds
        self.user_agent = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
        )

    @property
    def is_configured(self) -> bool:
        return bool(self.provider_name and self.api_key)

    def generate_video(
        self,
        *,
        project_id: str,
        scene_index: int,
        prompt: str,
        references: list[VideoReferenceInput],
    ) -> GeneratedVideo:
        self._require_configured()
        uploaded_references = self._prepare_references(project_id, references[: self.reference_limit])
        if not uploaded_references:
            raise VideoProviderError("Attach at least one keyframe or reference image before generating a video.")

        video_inputs = self._video_input_images(uploaded_references)
        request_prompt = self._build_request_prompt(prompt, video_inputs)
        created = self._create_video(
            project_id=project_id,
            scene_index=scene_index,
            prompt=request_prompt,
            images=video_inputs,
        )
        video_url = self._extract_url(created)
        job_id = self._extract_job_id(created)
        status = self._extract_status(created)
        if video_url:
            return self._result(
                video_url=video_url,
                job_id=job_id,
                status="VIDEO_READY",
                message=None,
                raw_response=created,
                references=uploaded_references,
            )
        if not job_id:
            raise VideoProviderError("Video provider accepted the request but did not return a video URL or job id.")
        return self.poll_video(project_id=project_id, job_id=job_id, references=uploaded_references, initial_status=status)

    def poll_video(
        self,
        *,
        project_id: str,
        job_id: str,
        references: list[VideoReferenceUpload] | None = None,
        initial_status: str | None = None,
    ) -> GeneratedVideo:
        self._require_configured()
        deadline = time.monotonic() + self.poll_timeout_seconds
        last_response: dict[str, Any] = {"id": job_id, "status": initial_status or "processing"}

        while time.monotonic() <= deadline:
            last_response = self._get_video_status(project_id=project_id, job_id=job_id)
            video_url = self._extract_url(last_response)
            status = self._extract_status(last_response)
            if video_url:
                return self._result(
                    video_url=video_url,
                    job_id=job_id,
                    status="VIDEO_READY",
                    message=None,
                    raw_response=last_response,
                    references=references or [],
                )
            if self._is_failed_status(status):
                message = self._extract_message(last_response) or f"Video job {job_id} failed."
                raise VideoProviderError(message)
            time.sleep(self.poll_interval_seconds)

        return self._result(
            video_url=None,
            job_id=job_id,
            status="PROCESSING",
            message=f"Video job {job_id} is still processing. Run Generate again later to poll the result.",
            raw_response=last_response,
            references=references or [],
        )

    def _require_configured(self) -> None:
        if not self.is_configured:
            raise VideoProviderError("Video provider is not configured. Set VIDEO_PROVIDER_NAME and VIDEO_PROVIDER_API_KEY.")
        if self.provider_name.lower() not in {"79ai", "gommo", "veo_omni", "omni"}:
            raise VideoProviderError("Unsupported video provider. Use VIDEO_PROVIDER_NAME=79ai for VEO Omni Flash.")

    def _prepare_references(self, project_id: str, references: list[VideoReferenceInput]) -> list[VideoReferenceUpload]:
        uploaded: list[VideoReferenceUpload] = []
        for reference in references:
            if reference.url and reference.url.startswith(("http://", "https://")):
                uploaded.append(
                    VideoReferenceUpload(label=reference.label, role=reference.role, url=reference.url, source=reference.url)
                )
                continue
            if not reference.file_path:
                continue
            path = Path(reference.file_path)
            if not path.exists():
                raise VideoProviderError(f"Reference image file is missing: {reference.label}")
            remote_url = self._upload_image(
                project_id=project_id,
                path=path,
                content_type=reference.content_type,
            )
            uploaded.append(VideoReferenceUpload(label=reference.label, role=reference.role, url=remote_url, source=str(path)))
        return uploaded

    def _upload_image(self, *, project_id: str, path: Path, content_type: str | None) -> str:
        image_bytes = path.read_bytes()
        fields = {
            "access_token": self.api_key,
            "domain": self.domain,
            "data": base64.b64encode(image_bytes).decode("ascii"),
            "project_id": project_id,
            "file_name": path.name,
            "size": str(len(image_bytes)),
        }
        data = self._post_form(f"{self.base_url}/ai/image-upload", fields)
        url = self._extract_url(data)
        if not url:
            raise VideoProviderError(f"Image upload succeeded but no public URL was returned for {path.name}.")
        return url

    def _create_video(
        self,
        *,
        project_id: str,
        scene_index: int,
        prompt: str,
        images: list[VideoReferenceUpload],
    ) -> dict[str, Any]:
        fields = {
            "access_token": self.api_key,
            "domain": self.domain,
            "project_id": project_id,
            "scene_index": str(scene_index),
            "model": self.model_id,
            "privacy": "PRIVATE",
            "ratio": self.ratio,
            "resolution": self.resolution,
            "duration": self.duration,
            "mode": self.mode,
            "prompt": prompt,
            "translate_to_en": self.translate_to_en,
            "images": json.dumps([reference.url for reference in images], ensure_ascii=False),
        }
        return self._post_form(f"{self.base_url}/ai/create-video", fields)

    def _get_video_status(self, *, project_id: str, job_id: str) -> dict[str, Any]:
        fields = {
            "access_token": self.api_key,
            "domain": self.domain,
            "project_id": project_id,
            "id": job_id,
            "id_base": job_id,
        }
        return self._post_form(f"{self.base_url}/ai/video", fields)

    def _post_form(self, url: str, fields: dict[str, str]) -> dict[str, Any]:
        body = urllib.parse.urlencode(fields).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=body,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Accept": "application/json, text/plain, */*",
                "Content-Type": "application/x-www-form-urlencoded",
                "User-Agent": self.user_agent,
            },
            method="POST",
        )
        return self._read_json_response(request)

    def _read_json_response(self, request: urllib.request.Request) -> dict[str, Any]:
        try:
            with urllib.request.urlopen(request, timeout=self.request_timeout_seconds) as response:
                body = response.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as exc:
            error_body = exc.read().decode("utf-8", errors="replace")
            raise VideoProviderError(f"Video provider HTTP {exc.code}: {error_body[:500]}") from exc
        except urllib.error.URLError as exc:
            raise VideoProviderError(f"Video provider request failed: {exc.reason}") from exc

        try:
            data = json.loads(body)
        except json.JSONDecodeError as exc:
            raise VideoProviderError(f"Video provider returned non-JSON response: {body[:300]}") from exc
        if not isinstance(data, dict):
            raise VideoProviderError("Video provider returned an invalid response.")
        self._raise_provider_error(data)
        return data

    def _raise_provider_error(self, data: dict[str, Any]) -> None:
        status = self._extract_status(data)
        if self._is_failed_status(status):
            raise VideoProviderError(self._extract_message(data) or "Video provider returned a failed status.")
        if data.get("error") and not self._extract_url(data):
            error = data.get("error")
            provider_message = self._extract_message(data)
            if provider_message:
                message = provider_message
            elif isinstance(error, dict):
                message = error.get("message") or error.get("detail") or json.dumps(error, ensure_ascii=False)
            else:
                message = str(error)
            raise VideoProviderError(message)
        if data.get("success") is False and not self._extract_url(data):
            raise VideoProviderError(self._extract_message(data) or "Video provider request was not accepted.")

    def _video_input_images(self, references: list[VideoReferenceUpload]) -> list[VideoReferenceUpload]:
        keyframes = [reference for reference in references if reference.role == "keyframe"]
        return (keyframes or references)[:2]

    def _build_request_prompt(self, prompt: str, images: list[VideoReferenceUpload]) -> str:
        image_lines: list[str]
        if len(images) >= 2:
            image_lines = [
                f"Image 1 is the first frame: {images[0].label}.",
                f"Image 2 is the end frame: {images[1].label}.",
            ]
        elif len(images) == 1:
            image_lines = [f"Image 1 is the first frame / main keyframe: {images[0].label}."]
        else:
            image_lines = ["No image input is attached."]

        return "\n".join(
            [
                f"Create exactly one {self.duration}-second vertical {self.ratio} ad clip.",
                f"Model mode: {self.mode}.",
                "Attached image inputs:",
                *image_lines,
                "",
                self._strip_manual_image_mentions(prompt),
                "",
                "Use the attached image input as the visual anchor for this one clip. Preserve actor identity, location layout, app/product UI, keyframe composition, voice/subtitle text, overlay intent, and negative rules.",
            ]
        )

    def _strip_manual_image_mentions(self, prompt: str) -> str:
        lines: list[str] = []
        skip_image_block = False
        for raw_line in prompt.strip().splitlines():
            line = raw_line.strip()
            if line.lower().startswith("image input for"):
                skip_image_block = True
                continue
            if skip_image_block and line.startswith("-"):
                continue
            if skip_image_block and not line:
                skip_image_block = False
                continue
            skip_image_block = False
            lines.append(raw_line)
        return "\n".join(lines).strip()

    def _result(
        self,
        *,
        video_url: str | None,
        job_id: str | None,
        status: str,
        message: str | None,
        raw_response: dict[str, Any],
        references: list[VideoReferenceUpload],
    ) -> GeneratedVideo:
        return GeneratedVideo(
            video_url=video_url,
            job_id=job_id,
            status=status,
            message=message,
            raw_response=raw_response,
            references=references,
            provider_name=self.provider_name,
            model_id=self.model_id,
            ratio=self.ratio,
            duration=self.duration,
            mode=self.mode,
            resolution=self.resolution,
        )

    def _extract_url(self, data: Any) -> str | None:
        if isinstance(data, str):
            if data.startswith(("http://", "https://")):
                return data
            return None
        if isinstance(data, list):
            for item in data:
                found = self._extract_url(item)
                if found:
                    return found
            return None
        if not isinstance(data, dict):
            return None
        for key in ("video_url", "videoUrl", "url", "file_url", "fileUrl", "download_url", "downloadUrl", "output_url", "result_url"):
            value = data.get(key)
            if isinstance(value, str) and value.startswith(("http://", "https://")):
                return value
        for key in ("data", "result", "imageInfo", "video", "videoInfo", "file", "output", "outputs"):
            found = self._extract_url(data.get(key))
            if found:
                return found
        return None

    def _extract_job_id(self, data: Any) -> str | None:
        if isinstance(data, list):
            for item in data:
                found = self._extract_job_id(item)
                if found:
                    return found
            return None
        if not isinstance(data, dict):
            return None
        for key in ("id_base", "job_id", "jobId", "task_id", "taskId", "request_id", "requestId", "id"):
            value = data.get(key)
            if isinstance(value, (str, int)) and str(value).strip():
                return str(value)
        for key in ("data", "result", "imageInfo", "video", "videoInfo", "task", "job"):
            found = self._extract_job_id(data.get(key))
            if found:
                return found
        return None

    def _extract_status(self, data: Any) -> str:
        if isinstance(data, list):
            for item in data:
                status = self._extract_status(item)
                if status:
                    return status
            return ""
        if not isinstance(data, dict):
            return ""
        for key in ("status", "state", "task_status", "job_status"):
            value = data.get(key)
            if isinstance(value, str):
                return value.strip().lower()
        for key in ("data", "result", "imageInfo", "video", "videoInfo", "task", "job"):
            status = self._extract_status(data.get(key))
            if status:
                return status
        return ""

    def _extract_message(self, data: Any) -> str | None:
        if isinstance(data, str):
            return data.strip() or None
        if isinstance(data, list):
            for item in data:
                found = self._extract_message(item)
                if found:
                    return found
            return None
        if not isinstance(data, dict):
            return None
        for key in ("message", "msg", "detail", "error_message", "status_message"):
            value = data.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        error = data.get("error")
        if isinstance(error, dict):
            return self._extract_message(error)
        if isinstance(error, str) and error.strip():
            return error.strip()
        for key in ("data", "result", "imageInfo", "video", "videoInfo", "task", "job"):
            found = self._extract_message(data.get(key))
            if found:
                return found
        return None

    def _is_failed_status(self, status: str) -> bool:
        if not status:
            return False
        normalized = status.lower()
        return any(token in normalized for token in ("failed", "failure", "error", "cancelled", "canceled", "rejected"))
