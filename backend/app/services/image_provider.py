import base64
import json
import urllib.error
import urllib.request
from dataclasses import dataclass

from app.config import IMAGE_MODEL_ID, IMAGE_PROVIDER_API_KEY, IMAGE_PROVIDER_BASE_URL, IMAGE_PROVIDER_NAME


class ImageProviderError(Exception):
    pass


@dataclass
class GeneratedImage:
    content: bytes
    content_type: str = "image/png"
    warning: str | None = None


class OpenAICompatibleImageProvider:
    def __init__(
        self,
        *,
        provider_name: str = IMAGE_PROVIDER_NAME,
        api_key: str = IMAGE_PROVIDER_API_KEY,
        base_url: str = IMAGE_PROVIDER_BASE_URL,
        model_id: str = IMAGE_MODEL_ID,
        timeout_seconds: int = 120,
    ) -> None:
        self.provider_name = provider_name.strip()
        self.api_key = api_key.strip()
        self.base_url = base_url.rstrip("/")
        self.model_id = model_id
        self.timeout_seconds = timeout_seconds

    @property
    def is_configured(self) -> bool:
        return bool(self.provider_name and self.api_key)

    def generate_image(self, *, prompt: str, aspect_ratio: str = "9:16") -> GeneratedImage:
        if not self.is_configured:
            raise ImageProviderError("Image provider is not configured. Set IMAGE_PROVIDER_NAME and IMAGE_PROVIDER_API_KEY.")

        payload = {
            "model": self.model_id,
            "prompt": prompt,
            "n": 1,
            "size": self._resolve_size(aspect_ratio),
            "response_format": "b64_json",
        }
        request = urllib.request.Request(
            f"{self.base_url}/images/generations",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                body = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            error_body = exc.read().decode("utf-8", errors="replace")
            raise ImageProviderError(f"Image provider HTTP {exc.code}: {error_body[:500]}") from exc
        except urllib.error.URLError as exc:
            raise ImageProviderError(f"Image provider request failed: {exc.reason}") from exc

        data = json.loads(body)
        item = (data.get("data") or [None])[0]
        if not isinstance(item, dict):
            raise ImageProviderError("Image provider returned no image data.")

        b64_json = item.get("b64_json")
        if isinstance(b64_json, str) and b64_json.strip():
            return GeneratedImage(content=base64.b64decode(b64_json.replace("data:image/png;base64,", "")))

        url = item.get("url")
        if isinstance(url, str) and url.strip():
            return self._download_image(url)

        raise ImageProviderError("Image provider response did not include b64_json or url.")

    def _download_image(self, url: str) -> GeneratedImage:
        request = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
            content_type = response.headers.get("content-type") or "image/png"
            return GeneratedImage(content=response.read(), content_type=content_type)

    def _resolve_size(self, aspect_ratio: str) -> str:
        if aspect_ratio == "16:9":
            return "1792x1024"
        if aspect_ratio == "1:1":
            return "1024x1024"
        return "1024x1792"
