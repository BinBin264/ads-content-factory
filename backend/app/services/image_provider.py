import base64
import json
import mimetypes
import urllib.error
import urllib.request
import uuid
from io import BytesIO
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence

from PIL import Image, UnidentifiedImageError

from app.config import (
    IMAGE_OUTPUT_SIZE,
    IMAGE_PROVIDER_API_KEY,
    IMAGE_PROVIDER_BASE_URL,
    IMAGE_PROVIDER_NAME,
)


class ImageProviderError(Exception):
    pass


@dataclass(frozen=True)
class ImageReference:
    id: str
    label: str
    role: str
    file_path: str | None = None
    url: str | None = None
    content_type: str | None = None


@dataclass
class GeneratedImage:
    content: bytes
    content_type: str = "image/png"
    warning: str | None = None
    source_url: str | None = None
    width: int | None = None
    height: int | None = None


class OpenAICompatibleImageProvider:
    SHOPAIKEY_PROVIDER_NAMES = {"shopaikey", "shopaikey-google", "shopaikey_google", "nano-banana"}
    SHOPAIKEY_GOOGLE_MODEL_IDS = frozenset({"nano-banana", "nano-banana-2", "nano-banana-pro"})
    SHOPAIKEY_OPENAI_MODEL_IDS = frozenset({
        "gpt-image-1",
        "gpt-image-1.5",
        "gpt-image-2",
        "gpt-image-2-all",
    })

    def __init__(
        self,
        *,
        provider_name: str = IMAGE_PROVIDER_NAME,
        api_key: str = IMAGE_PROVIDER_API_KEY,
        base_url: str = IMAGE_PROVIDER_BASE_URL,
        image_output_size: str = IMAGE_OUTPUT_SIZE,
        timeout_seconds: int = 180,
    ) -> None:
        self.provider_name = provider_name.strip().lower()
        self.api_key = api_key.strip()
        self.base_url = base_url.rstrip("/")
        self.image_output_size = image_output_size.strip().upper() or "2K"
        self.timeout_seconds = timeout_seconds
        self._uploaded_reference_cache: dict[tuple[str, int, int], str] = {}

    @property
    def is_configured(self) -> bool:
        return bool(self.provider_name and self.api_key)

    @property
    def is_shopaikey_google(self) -> bool:
        return self.provider_name in self.SHOPAIKEY_PROVIDER_NAMES

    def generate_image(
        self,
        *,
        prompt: str,
        model_id: str,
        aspect_ratio: str = "9:16",
        reference_images: Sequence[ImageReference] | None = None,
        progress_callback: Callable[[int, str], None] | None = None,
    ) -> GeneratedImage:
        if not self.is_configured:
            raise ImageProviderError(
                "Image provider is not configured. Set IMAGE_PROVIDER_NAME and IMAGE_PROVIDER_API_KEY."
            )

        references = list(reference_images or [])
        selected_model = self.resolve_model_id(model_id)
        if self.is_shopaikey_google:
            if selected_model in self.SHOPAIKEY_GOOGLE_MODEL_IDS:
                return self._generate_shopaikey_google(
                    prompt,
                    aspect_ratio,
                    selected_model,
                    references,
                    progress_callback,
                )
            return self._generate_shopaikey_openai(
                prompt,
                aspect_ratio,
                selected_model,
                references,
                progress_callback,
            )
        if references:
            raise ImageProviderError(
                "The configured image provider does not support reference images. "
                "Use IMAGE_PROVIDER_NAME=shopaikey-google for storyboard image-to-image generation."
            )
        return self._generate_openai_compatible(prompt, aspect_ratio, selected_model, progress_callback)

    def resolve_model_id(self, model_id: str) -> str:
        selected_model = str(model_id).strip()
        if not selected_model:
            raise ImageProviderError("Select an image model in Automation mode before generating an image.")
        allowed_models = self.SHOPAIKEY_GOOGLE_MODEL_IDS | self.SHOPAIKEY_OPENAI_MODEL_IDS
        if self.is_shopaikey_google and selected_model not in allowed_models:
            allowed = ", ".join(sorted(allowed_models))
            raise ImageProviderError(f"Unsupported ShopAIKey image model '{selected_model}'. Choose one of: {allowed}.")
        return selected_model

    def _generate_shopaikey_google(
        self,
        prompt: str,
        aspect_ratio: str,
        model_id: str,
        references: list[ImageReference],
        progress_callback: Callable[[int, str], None] | None,
    ) -> GeneratedImage:
        if len(references) > 5:
            raise ImageProviderError("ShopAIKey Gemini Image supports at most 5 reference images per request.")

        self._report_progress(progress_callback, 15, "Preparing reference images")
        reference_urls: list[str] = []
        for index, reference in enumerate(references, start=1):
            reference_urls.append(self._resolve_reference_url(reference))
            reference_progress = 15 + round((index / max(1, len(references))) * 25)
            self._report_progress(progress_callback, reference_progress, f"Uploaded reference {index}/{len(references)}")
        payload = {
            "model": model_id,
            "prompt": self._decorate_prompt_with_reference_map(
                self._decorate_prompt_with_aspect_ratio(prompt, aspect_ratio),
                references,
            ),
            "size": aspect_ratio,
            "format": "png",
            "response_format": "url",
            "image_urls": reference_urls,
        }
        if model_id != "nano-banana":
            payload["imageSize"] = self.image_output_size
        self._report_progress(progress_callback, 50, "Provider generating image")
        data = self._request_json(
            f"{self._shopaikey_root_url()}/images/google/generations",
            payload,
            operation="image generation",
        )
        self._report_progress(progress_callback, 85, "Downloading generated image")
        generated = self._generated_image_from_response(data)
        self._report_progress(progress_callback, 90, "Validating generated image")
        self._validate_aspect_ratio(generated, aspect_ratio)
        return generated

    def _generate_shopaikey_openai(
        self,
        prompt: str,
        aspect_ratio: str,
        model_id: str,
        references: list[ImageReference],
        progress_callback: Callable[[int, str], None] | None,
    ) -> GeneratedImage:
        if len(references) > 4:
            raise ImageProviderError("ShopAIKey GPT Image supports at most 4 reference images per request.")

        self._report_progress(progress_callback, 15, "Preparing reference images")
        reference_urls: list[str] = []
        for index, reference in enumerate(references, start=1):
            reference_urls.append(self._resolve_reference_url(reference))
            reference_progress = 15 + round((index / max(1, len(references))) * 25)
            self._report_progress(progress_callback, reference_progress, f"Uploaded reference {index}/{len(references)}")

        provider_size, provider_ratio = self._resolve_shopaikey_openai_size(aspect_ratio)
        payload = {
            "model": model_id,
            "prompt": self._decorate_prompt_with_reference_map(
                self._decorate_prompt_for_openai_portrait(prompt, aspect_ratio, provider_size),
                references,
            ),
            "n": 1,
            "size": provider_size,
            "format": "png",
            "response_format": "url",
            "image_urls": reference_urls,
        }
        self._report_progress(progress_callback, 50, "Provider generating image")
        data = self._request_json(
            f"{self._shopaikey_root_url()}/images/openai/generations",
            payload,
            operation="GPT image generation",
        )
        self._report_progress(progress_callback, 85, "Downloading generated image")
        generated = self._generated_image_from_response(data)
        self._report_progress(progress_callback, 90, "Validating generated image")
        self._validate_aspect_ratio(generated, provider_ratio)
        if provider_ratio != aspect_ratio:
            generated.warning = (
                f"{model_id} returned its supported {provider_ratio} portrait canvas. "
                f"The prompt reserved a centered {aspect_ratio} safe area for the video crop."
            )
        return generated

    def _generate_openai_compatible(
        self,
        prompt: str,
        aspect_ratio: str,
        model_id: str,
        progress_callback: Callable[[int, str], None] | None,
    ) -> GeneratedImage:
        payload = {
            "model": model_id,
            "prompt": prompt,
            "n": 1,
            "size": self._resolve_openai_size(aspect_ratio),
            "response_format": "b64_json",
        }
        self._report_progress(progress_callback, 50, "Provider generating image")
        data = self._request_json(
            f"{self.base_url}/images/generations",
            payload,
            operation="image generation",
        )
        self._report_progress(progress_callback, 85, "Downloading generated image")
        return self._generated_image_from_response(data)

    def _report_progress(
        self,
        callback: Callable[[int, str], None] | None,
        progress: int,
        phase: str,
    ) -> None:
        if callback:
            callback(progress, phase)

    def _resolve_reference_url(self, reference: ImageReference) -> str:
        if reference.file_path:
            path = Path(reference.file_path).resolve()
            if not path.is_file():
                raise ImageProviderError(f"Reference image is missing: {reference.label}")
            stat = path.stat()
            cache_key = (str(path), stat.st_mtime_ns, stat.st_size)
            cached_url = self._uploaded_reference_cache.get(cache_key)
            if cached_url:
                return cached_url
            uploaded_url = self._upload_reference_image(path, reference.content_type)
            self._uploaded_reference_cache[cache_key] = uploaded_url
            return uploaded_url

        url = str(reference.url or "").strip()
        if url.startswith("https://") or url.startswith("http://") or url.startswith("data:image/"):
            return url
        raise ImageProviderError(f"Reference image has no accessible file or public URL: {reference.label}")

    def _upload_reference_image(self, path: Path, content_type: str | None) -> str:
        content = path.read_bytes()
        if len(content) > 20 * 1024 * 1024:
            raise ImageProviderError(f"Reference image exceeds ShopAIKey's 20MB upload limit: {path.name}")

        boundary = f"----AIVideoFactory{uuid.uuid4().hex}"
        mime_type = content_type or mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        safe_name = path.name.replace('"', "")
        body = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="{safe_name}"\r\n'
            f"Content-Type: {mime_type}\r\n\r\n"
        ).encode("utf-8") + content + f"\r\n--{boundary}--\r\n".encode("utf-8")
        request = urllib.request.Request(
            f"{self._shopaikey_root_url()}/upload/images",
            data=body,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": f"multipart/form-data; boundary={boundary}",
            },
            method="POST",
        )
        response = self._open_json(request, operation=f"reference upload ({path.name})")
        url = str(response.get("url") or "").strip()
        if not url:
            raise ImageProviderError("ShopAIKey reference upload did not return a public URL.")
        return url

    def _request_json(self, url: str, payload: dict, *, operation: str) -> dict:
        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        return self._open_json(request, operation=operation)

    def _open_json(self, request: urllib.request.Request, *, operation: str) -> dict:
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                body = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            error_body = exc.read().decode("utf-8", errors="replace").replace(self.api_key, "[redacted]")
            raise ImageProviderError(f"Image provider {operation} HTTP {exc.code}: {error_body[:1000]}") from exc
        except TimeoutError as exc:
            raise ImageProviderError(f"Image provider {operation} timed out after {self.timeout_seconds} seconds.") from exc
        except urllib.error.URLError as exc:
            raise ImageProviderError(f"Image provider {operation} request failed: {exc.reason}") from exc

        try:
            data = json.loads(body)
        except json.JSONDecodeError as exc:
            raise ImageProviderError(f"Image provider {operation} returned invalid JSON.") from exc
        if not isinstance(data, dict):
            raise ImageProviderError(f"Image provider {operation} returned an invalid response object.")
        return data

    def _generated_image_from_response(self, data: dict) -> GeneratedImage:
        item = (data.get("data") or [None])[0]
        if not isinstance(item, dict):
            raise ImageProviderError("Image provider returned no image data.")

        b64_json = item.get("b64_json")
        if isinstance(b64_json, str) and b64_json.strip():
            encoded = b64_json.split(",", 1)[-1]
            try:
                return self._generated_image_from_bytes(base64.b64decode(encoded))
            except ValueError as exc:
                raise ImageProviderError("Image provider returned invalid base64 image data.") from exc

        url = item.get("url")
        if isinstance(url, str) and url.strip():
            generated = self._download_image(url)
            generated.source_url = url
            return generated

        raise ImageProviderError("Image provider response did not include b64_json or url.")

    def _download_image(self, url: str) -> GeneratedImage:
        request = urllib.request.Request(url, method="GET")
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                content_type = (response.headers.get("content-type") or "image/png").split(";", 1)[0]
                return self._generated_image_from_bytes(response.read(), content_type=content_type)
        except urllib.error.HTTPError as exc:
            raise ImageProviderError(f"Generated image download HTTP {exc.code}.") from exc
        except urllib.error.URLError as exc:
            raise ImageProviderError(f"Generated image download failed: {exc.reason}") from exc

    def _decorate_prompt_with_reference_map(
        self,
        prompt: str,
        references: Sequence[ImageReference],
    ) -> str:
        if not references:
            return prompt
        mapping = "\n".join(
            f"- Image {index}: @{reference.label} is the {reference.role} reference. "
            "Preserve only the identity, layout, or product appearance assigned to this role."
            for index, reference in enumerate(references, start=1)
        )
        return (
            f"{prompt.rstrip()}\n\n"
            "Attached reference image map (in exact image_urls order):\n"
            f"{mapping}\n"
            "Do not combine the references as a collage. Compose one coherent frame and do not import unrelated details from a reference. "
            "When a role is pixel-locked product/app UI, place that exact visible design inside the product or phone screen: preserve its layout, "
            "colors, logo, text, controls, and screen state; do not redraw, reinterpret, merge, or invent another interface."
        )

    def _decorate_prompt_with_aspect_ratio(self, prompt: str, aspect_ratio: str) -> str:
        orientation = "portrait/vertical" if self._target_ratio(aspect_ratio) < 1 else "landscape/horizontal"
        return (
            f"{prompt.rstrip()}\n\n"
            f"Output format requirement: compose and return exactly one {orientation} image at {aspect_ratio}. "
            "Frame every important subject and product inside that aspect ratio. Do not return a rotated image, "
            "a different aspect ratio, letterboxing, borders, a collage, or a contact sheet."
        )

    def _decorate_prompt_for_openai_portrait(
        self,
        prompt: str,
        target_aspect_ratio: str,
        provider_size: str,
    ) -> str:
        if self._target_ratio(target_aspect_ratio) >= 1:
            return (
                f"{prompt.rstrip()}\n\n"
                f"Output canvas requirement: create one coherent image at {provider_size}. "
                "Do not return borders, letterboxing, a collage, or a contact sheet."
            )
        return (
            f"{prompt.rstrip()}\n\n"
            f"Output canvas requirement: create one coherent portrait image at {provider_size}. "
            f"Compose all critical faces, hands, products, phones, and readable UI inside a centered {target_aspect_ratio} safe area "
            "so the frame can be cropped vertically without losing required content. Do not return borders, letterboxing, "
            "a collage, or a contact sheet."
        )

    def _generated_image_from_bytes(self, content: bytes, content_type: str = "image/png") -> GeneratedImage:
        width = None
        height = None
        try:
            with Image.open(BytesIO(content)) as image:
                width, height = image.size
        except (UnidentifiedImageError, OSError):
            pass
        return GeneratedImage(content=content, content_type=content_type, width=width, height=height)

    def _validate_aspect_ratio(self, generated: GeneratedImage, aspect_ratio: str) -> None:
        if not generated.width or not generated.height:
            return
        target = self._target_ratio(aspect_ratio)
        actual = generated.width / generated.height
        if abs(actual - target) / target <= 0.04:
            return
        raise ImageProviderError(
            "Image provider returned "
            f"{generated.width}x{generated.height} ({actual:.3f}) while {aspect_ratio} ({target:.3f}) was requested. "
            "The image was rejected so it cannot replace the current reference. Regenerate or check the provider's aspect-ratio support."
        )

    def _target_ratio(self, aspect_ratio: str) -> float:
        try:
            width, height = (int(part) for part in aspect_ratio.split(":", 1))
        except (TypeError, ValueError) as exc:
            raise ImageProviderError(f"Invalid image aspect ratio: {aspect_ratio}") from exc
        if width <= 0 or height <= 0:
            raise ImageProviderError(f"Invalid image aspect ratio: {aspect_ratio}")
        return width / height

    def _shopaikey_root_url(self) -> str:
        return self.base_url[:-3] if self.base_url.endswith("/v1") else self.base_url

    def _resolve_shopaikey_openai_size(self, aspect_ratio: str) -> tuple[str, str]:
        target = self._target_ratio(aspect_ratio)
        if target < 0.9:
            return "1024x1536", "2:3"
        if target > 1.1:
            return "1536x1024", "3:2"
        return "1024x1024", "1:1"

    def _resolve_openai_size(self, aspect_ratio: str) -> str:
        if aspect_ratio == "16:9":
            return "1792x1024"
        if aspect_ratio == "1:1":
            return "1024x1024"
        return "1024x1792"
