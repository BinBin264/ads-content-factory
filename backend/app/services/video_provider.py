import json
import mimetypes
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.config import (
    VIDEO_ENABLE_UPSAMPLE,
    VIDEO_ENHANCE_PROMPT,
    VIDEO_MODEL_ID,
    VIDEO_MODEL_RATIO,
    VIDEO_PROVIDER_API_KEY,
    VIDEO_PROVIDER_BASE_URL,
    VIDEO_PROVIDER_NAME,
    VIDEO_REFERENCE_LIMIT,
    VIDEO_REQUEST_TIMEOUT_SECONDS,
)


class VideoProviderError(Exception):
    pass


class VideoTaskFailedError(VideoProviderError):
    """The provider reached a terminal failure state for an existing task."""


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


@dataclass(frozen=True)
class VideoModelProfile:
    model_id: str
    family: str
    ratio: str
    duration: str
    mode: str
    resolution: str


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
    progress: int


class ShopAIKeyVideoProvider:
    """ShopAIKey Veo/Grok provider using one selected keyframe as the visual anchor."""

    SUPPORTED_PROVIDER_NAMES = {"shopaikey", "shop-ai-key", "shop_ai_key"}
    SUPPORTED_MODEL_IDS = {
        "veo3.1-pro",
        "veo3.1-fast",
        "veo3.1-fast-components",
        "grok-video-3",
        "grok-video-3-10s",
    }

    def __init__(
        self,
        *,
        provider_name: str = VIDEO_PROVIDER_NAME,
        api_key: str = VIDEO_PROVIDER_API_KEY,
        base_url: str = VIDEO_PROVIDER_BASE_URL,
        model_id: str = VIDEO_MODEL_ID,
        ratio: str = VIDEO_MODEL_RATIO,
        enhance_prompt: bool = VIDEO_ENHANCE_PROMPT,
        enable_upsample: bool = VIDEO_ENABLE_UPSAMPLE,
        reference_limit: int = VIDEO_REFERENCE_LIMIT,
        request_timeout_seconds: int = VIDEO_REQUEST_TIMEOUT_SECONDS,
    ) -> None:
        self.provider_name = provider_name.strip().lower()
        self.api_key = api_key.strip()
        self.base_url = base_url.rstrip("/")
        self.model_id = model_id.strip() or "veo3.1-pro"
        self.ratio = ratio.strip() or "9:16"
        self.enhance_prompt = bool(enhance_prompt)
        self.enable_upsample = bool(enable_upsample)
        self.reference_limit = max(1, min(reference_limit, 2))
        self.request_timeout_seconds = max(15, request_timeout_seconds)
        self._uploaded_reference_cache: dict[tuple[str, int, int], str] = {}

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
        duration: str | None = None,
        model_id: str | None = None,
    ) -> GeneratedVideo:
        self._require_configured()
        profile = self.get_model_profile(model_id=model_id, duration=duration)
        uploaded_references = self._prepare_references(references[: self.reference_limit])
        video_inputs = self._video_input_images(uploaded_references)
        if not video_inputs:
            raise VideoProviderError("Select or upload one keyframe image before generating a video.")

        request_prompt = self._build_request_prompt(prompt, video_inputs[0])
        created = self._create_video(prompt=request_prompt, images=video_inputs, profile=profile)
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
                references=video_inputs,
                profile=profile,
                progress=100,
            )
        if not job_id:
            raise VideoProviderError("ShopAIKey accepted the request but did not return a result URL or task_id.")
        return self._result(
            video_url=None,
            job_id=job_id,
            status=self._public_processing_status(status),
            message="ShopAIKey accepted the video task. Poll its status to get provider progress.",
            raw_response=created,
            references=video_inputs,
            profile=profile,
            progress=self._extract_progress(created),
        )

    def poll_video(
        self,
        *,
        project_id: str,
        job_id: str,
        references: list[VideoReferenceUpload] | None = None,
        initial_status: str | None = None,
        duration: str | None = None,
        model_id: str | None = None,
    ) -> GeneratedVideo:
        del project_id
        self._require_configured()
        profile = self.get_model_profile(model_id=model_id, duration=duration)
        last_response = self._get_video_status(job_id)
        video_url = self._extract_url(last_response)
        status = self._extract_status(last_response) or str(initial_status or "processing").lower()
        if video_url or status == "success":
            if not video_url:
                raise VideoProviderError(f"ShopAIKey video task {job_id} succeeded without result_url.")
            return self._result(
                video_url=video_url,
                job_id=job_id,
                status="VIDEO_READY",
                message=None,
                raw_response=last_response,
                references=references or [],
                profile=profile,
                progress=100,
            )
        return self._result(
            video_url=None,
            job_id=job_id,
            status=self._public_processing_status(status),
            message=f"ShopAIKey video task {job_id} is still processing.",
            raw_response=last_response,
            references=references or [],
            profile=profile,
            progress=self._extract_progress(last_response),
        )

    def get_model_profile(self, *, model_id: str | None = None, duration: str | None = None) -> VideoModelProfile:
        selected_model = str(model_id or self.model_id).strip()
        if selected_model not in self.SUPPORTED_MODEL_IDS:
            supported = ", ".join(sorted(self.SUPPORTED_MODEL_IDS))
            raise VideoProviderError(f"Unsupported video model '{selected_model}'. Supported models: {supported}.")

        selected_duration = self._normalize_duration(duration)
        if selected_model == "veo3.1-fast-components":
            return VideoModelProfile(
                model_id=selected_model,
                family="veo",
                ratio="16:9",
                duration=selected_duration,
                mode="components",
                resolution="provider upsample" if self.enable_upsample else "provider default",
            )
        if selected_model.startswith("grok-video"):
            return VideoModelProfile(
                model_id=selected_model,
                family="grok",
                ratio="2:3",
                duration="10" if selected_model == "grok-video-3-10s" else selected_duration,
                mode="image_to_video",
                resolution="1080P",
            )
        return VideoModelProfile(
            model_id=selected_model,
            family="veo",
            ratio=self.ratio,
            duration=selected_duration,
            mode="first_frame",
            resolution="provider upsample" if self.enable_upsample else "provider default",
        )

    def _require_configured(self) -> None:
        if not self.is_configured:
            raise VideoProviderError(
                "Video provider is not configured. Set IMAGE_PROVIDER_API_KEY or VIDEO_PROVIDER_API_KEY for ShopAIKey."
            )
        if self.provider_name not in self.SUPPORTED_PROVIDER_NAMES:
            raise VideoProviderError("Unsupported video provider. Set VIDEO_PROVIDER_NAME=shopaikey.")

    def _prepare_references(self, references: list[VideoReferenceInput]) -> list[VideoReferenceUpload]:
        uploaded: list[VideoReferenceUpload] = []
        for reference in references:
            if reference.url and reference.url.startswith(("http://", "https://")):
                uploaded.append(
                    VideoReferenceUpload(label=reference.label, role=reference.role, url=reference.url, source=reference.url)
                )
                continue
            if not reference.file_path:
                continue
            path = Path(reference.file_path).resolve()
            if not path.is_file():
                raise VideoProviderError(f"Reference image file is missing: {reference.label}")
            uploaded.append(
                VideoReferenceUpload(
                    label=reference.label,
                    role=reference.role,
                    url=self._upload_image(path, reference.content_type),
                    source=str(path),
                )
            )
        return uploaded

    def _upload_image(self, path: Path, content_type: str | None) -> str:
        stat = path.stat()
        cache_key = (str(path), stat.st_mtime_ns, stat.st_size)
        cached_url = self._uploaded_reference_cache.get(cache_key)
        if cached_url:
            return cached_url
        if stat.st_size > 20 * 1024 * 1024:
            raise VideoProviderError(f"Keyframe exceeds ShopAIKey's 20MB upload limit: {path.name}")

        content = path.read_bytes()
        boundary = f"----AIVideoFactory{uuid.uuid4().hex}"
        mime_type = content_type or mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        safe_name = path.name.replace('"', "")
        body = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="{safe_name}"\r\n'
            f"Content-Type: {mime_type}\r\n\r\n"
        ).encode("utf-8") + content + f"\r\n--{boundary}--\r\n".encode("utf-8")
        request = urllib.request.Request(
            f"{self._root_url()}/upload/images",
            data=body,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": f"multipart/form-data; boundary={boundary}",
            },
            method="POST",
        )
        response = self._read_json_response(request, operation=f"keyframe upload ({path.name})")
        url = self._extract_url(response)
        if not url:
            raise VideoProviderError(f"ShopAIKey uploaded {path.name} but returned no public image URL.")
        self._uploaded_reference_cache[cache_key] = url
        return url

    def _create_video(
        self,
        *,
        prompt: str,
        images: list[VideoReferenceUpload],
        profile: VideoModelProfile,
    ) -> dict[str, Any]:
        image_urls = [reference.url for reference in images]
        if profile.family == "grok":
            metadata: dict[str, Any] = {
                "images": image_urls,
                "duration": int(profile.duration),
                "ratio": profile.ratio,
                "resolution": profile.resolution,
            }
        else:
            metadata = {
                "images": image_urls,
                "aspect_ratio": profile.ratio,
                "enhance_prompt": self.enhance_prompt,
                "enable_upsample": self.enable_upsample,
            }
        payload = {"model": profile.model_id, "prompt": prompt, "metadata": metadata}
        return self._request_json(
            f"{self._v1_url()}/video/generations",
            method="POST",
            payload=payload,
            operation="video generation",
        )

    def _get_video_status(self, job_id: str) -> dict[str, Any]:
        return self._request_json(
            f"{self._v1_url()}/video/generations/{job_id}",
            method="GET",
            operation=f"video status ({job_id})",
        )

    def _request_json(
        self,
        url: str,
        *,
        method: str,
        payload: dict[str, Any] | None = None,
        operation: str,
    ) -> dict[str, Any]:
        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8") if payload is not None else None,
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {self.api_key}",
                **({"Content-Type": "application/json"} if payload is not None else {}),
            },
            method=method,
        )
        return self._read_json_response(request, operation=operation)

    def _read_json_response(self, request: urllib.request.Request, *, operation: str) -> dict[str, Any]:
        try:
            with urllib.request.urlopen(request, timeout=self.request_timeout_seconds) as response:
                body = response.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as exc:
            error_body = exc.read().decode("utf-8", errors="replace").replace(self.api_key, "[redacted]")
            raise VideoProviderError(f"ShopAIKey {operation} HTTP {exc.code}: {error_body[:1000]}") from exc
        except TimeoutError as exc:
            raise VideoProviderError(
                f"ShopAIKey {operation} timed out after {self.request_timeout_seconds} seconds."
            ) from exc
        except urllib.error.URLError as exc:
            raise VideoProviderError(f"ShopAIKey {operation} request failed: {exc.reason}") from exc

        try:
            data = json.loads(body)
        except json.JSONDecodeError as exc:
            raise VideoProviderError(f"ShopAIKey {operation} returned non-JSON data: {body[:300]}") from exc
        if not isinstance(data, dict):
            raise VideoProviderError(f"ShopAIKey {operation} returned an invalid response object.")
        self._raise_provider_error(data)
        return data

    def _raise_provider_error(self, data: dict[str, Any]) -> None:
        status = self._extract_status(data)
        if self._is_failed_status(status):
            raise VideoTaskFailedError(self._extract_message(data) or "ShopAIKey video task failed.")
        if data.get("error"):
            raise VideoProviderError(self._extract_message(data) or "ShopAIKey returned an error.")
        code = str(data.get("code") or "").strip().lower()
        if code and code not in {"success", "ok", "200"}:
            raise VideoProviderError(self._extract_message(data) or f"ShopAIKey returned code {code}.")

    def _video_input_images(self, references: list[VideoReferenceUpload]) -> list[VideoReferenceUpload]:
        keyframes = [reference for reference in references if reference.role == "keyframe"]
        return (keyframes or references)[:1]

    def _build_request_prompt(self, prompt: str, keyframe: VideoReferenceUpload) -> str:
        return "\n".join(
            [
                "Generate one coherent video clip from the attached main keyframe.",
                f"The attached image @{keyframe.label} is the first frame and visual source of truth.",
                "Continue naturally from that exact frame; do not create a collage, slideshow, visual reset, or alternate design.",
                "",
                self._strip_manual_image_mentions(prompt),
                "",
                "Preserve the keyframe's actor identity, face, outfit, location layout, lighting, product/app UI, product shape, logo, readable text, colors, and composition. Only animate the requested action and camera motion. Do not redesign any visible reference.",
            ]
        )

    def _strip_manual_image_mentions(self, prompt: str) -> str:
        lines: list[str] = []
        skip_image_block = False
        for raw_line in prompt.strip().splitlines():
            line = raw_line.strip()
            if line.lower().startswith(("image input for", "reference images to attach")):
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
        profile: VideoModelProfile,
        progress: int,
    ) -> GeneratedVideo:
        return GeneratedVideo(
            video_url=video_url,
            job_id=job_id,
            status=status,
            message=message,
            raw_response=raw_response,
            references=references,
            provider_name="ShopAIKey",
            model_id=profile.model_id,
            ratio=profile.ratio,
            duration=profile.duration,
            mode=profile.mode,
            resolution=profile.resolution,
            progress=max(0, min(100, progress)),
        )

    def _extract_progress(self, data: Any) -> int:
        if isinstance(data, list):
            return next((progress for item in data if (progress := self._extract_progress(item)) > 0), 0)
        if not isinstance(data, dict):
            return 0
        raw_progress = data.get("progress")
        if isinstance(raw_progress, str):
            cleaned = raw_progress.strip().removesuffix("%").strip()
            try:
                return max(0, min(100, int(float(cleaned))))
            except ValueError:
                pass
        if isinstance(raw_progress, (int, float)):
            return max(0, min(100, int(raw_progress)))
        for key in ("data", "result", "task", "job"):
            nested = self._extract_progress(data.get(key))
            if nested > 0:
                return nested
        return 100 if self._extract_status(data) == "success" else 0

    def _public_processing_status(self, status: str) -> str:
        return "QUEUED" if status in {"queued", "pending"} else "PROCESSING"

    def _normalize_duration(self, value: str | None) -> str:
        raw_value = str(value or "8").strip()
        allowed = ("4", "6", "8", "10")
        if raw_value in allowed:
            return raw_value
        try:
            raw_number = int(float(raw_value))
        except ValueError:
            return "8"
        return min(allowed, key=lambda item: abs(int(item) - raw_number))

    def _root_url(self) -> str:
        return self.base_url[:-3] if self.base_url.endswith("/v1") else self.base_url

    def _v1_url(self) -> str:
        return self.base_url if self.base_url.endswith("/v1") else f"{self.base_url}/v1"

    def _extract_url(self, data: Any) -> str | None:
        if isinstance(data, str):
            return data if data.startswith(("http://", "https://")) else None
        if isinstance(data, list):
            return next((found for item in data if (found := self._extract_url(item))), None)
        if not isinstance(data, dict):
            return None
        for key in ("result_url", "url", "video_url", "download_url", "output_url"):
            value = data.get(key)
            if isinstance(value, str) and value.startswith(("http://", "https://")):
                return value
        for key in ("data", "result", "video", "output", "outputs"):
            if found := self._extract_url(data.get(key)):
                return found
        return None

    def _extract_job_id(self, data: Any) -> str | None:
        if isinstance(data, list):
            return next((found for item in data if (found := self._extract_job_id(item))), None)
        if not isinstance(data, dict):
            return None
        for key in ("task_id", "job_id", "id"):
            value = data.get(key)
            if isinstance(value, (str, int)) and str(value).strip():
                return str(value)
        for key in ("data", "result", "task", "job"):
            if found := self._extract_job_id(data.get(key)):
                return found
        return None

    def _extract_status(self, data: Any) -> str:
        if isinstance(data, list):
            return next((status for item in data if (status := self._extract_status(item))), "")
        if not isinstance(data, dict):
            return ""
        for key in ("status", "state", "task_status", "job_status"):
            value = data.get(key)
            if isinstance(value, str):
                return value.strip().lower()
        for key in ("data", "result", "task", "job"):
            if status := self._extract_status(data.get(key)):
                return status
        return ""

    def _extract_message(self, data: Any) -> str | None:
        if isinstance(data, str):
            return data.strip() or None
        if isinstance(data, list):
            return next((found for item in data if (found := self._extract_message(item))), None)
        if not isinstance(data, dict):
            return None
        for key in ("fail_reason", "message", "detail", "error_message"):
            value = data.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        if found := self._extract_message(data.get("error")):
            return found
        for key in ("data", "result", "task", "job"):
            if found := self._extract_message(data.get(key)):
                return found
        return None

    def _is_failed_status(self, status: str) -> bool:
        return status.lower() in {"failure", "failed", "error", "cancelled", "canceled", "rejected"}
