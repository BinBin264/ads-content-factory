import json
import re
import threading
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Protocol, Sequence

from app.config import GEMINI_API_BASE_URL, GEMINI_API_KEYS, GEMINI_MODEL


class LLMProviderError(Exception):
    pass


class LLMProvider(Protocol):
    @property
    def is_configured(self) -> bool:
        ...

    def generate_json(
        self,
        prompt: str,
        *,
        temperature: float = 0.4,
        response_schema: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        ...

    def generate_json_parts(
        self,
        parts: list[dict[str, Any]],
        *,
        temperature: float = 0.3,
        response_schema: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        ...


class GeminiLLMProvider:
    def __init__(
        self,
        api_keys: Sequence[str] | None = None,
        model: str = GEMINI_MODEL,
        base_url: str = GEMINI_API_BASE_URL,
        timeout_seconds: int = 120,
    ) -> None:
        self.api_keys = [key.strip() for key in (api_keys if api_keys is not None else GEMINI_API_KEYS) if key.strip()]
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self._next_key_index = 0
        self._lock = threading.Lock()

    @property
    def is_configured(self) -> bool:
        return bool(self.api_keys)

    def generate_json(
        self,
        prompt: str,
        *,
        temperature: float = 0.4,
        response_schema: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not self.is_configured:
            raise LLMProviderError("GEMINI_API_KEYS is required for Plan Creation and content generation.")

        return self.generate_json_parts(
            [{"text": prompt}],
            temperature=temperature,
            response_schema=response_schema,
        )

    def generate_json_parts(
        self,
        parts: list[dict[str, Any]],
        *,
        temperature: float = 0.3,
        response_schema: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not self.is_configured:
            raise LLMProviderError("GEMINI_API_KEYS is required for Plan Creation and content generation.")

        last_error: LLMProviderError | None = None
        for _ in range(len(self.api_keys)):
            api_key = self._take_next_api_key()
            try:
                return self._generate_json_parts_with_key(
                    api_key,
                    parts,
                    temperature=temperature,
                    response_schema=response_schema,
                )
            except LLMProviderError as exc:
                last_error = exc
                if not self._should_try_next_key(exc):
                    raise

        if last_error:
            raise LLMProviderError(f"All configured Gemini API keys failed: {last_error}") from last_error
        raise LLMProviderError("Gemini request failed before an API key was selected")

    def _take_next_api_key(self) -> str:
        with self._lock:
            key = self.api_keys[self._next_key_index % len(self.api_keys)]
            self._next_key_index = (self._next_key_index + 1) % len(self.api_keys)
            return key

    def _generate_json_parts_with_key(
        self,
        api_key: str,
        parts: list[dict[str, Any]],
        *,
        temperature: float,
        response_schema: dict[str, Any] | None,
    ) -> dict[str, Any]:

        url = (
            f"{self.base_url}/models/{urllib.parse.quote(self.model, safe='')}:generateContent"
            f"?key={urllib.parse.quote(api_key)}"
        )
        generation_config: dict[str, Any] = {
            "temperature": temperature,
            "response_mime_type": "application/json",
        }
        if response_schema:
            generation_config["response_schema"] = response_schema

        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": parts,
                }
            ],
            "generationConfig": generation_config,
        }

        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                response_body = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            error_body = exc.read().decode("utf-8", errors="replace")
            raise LLMProviderError(f"Gemini API HTTP {exc.code}: {self._sanitize_error_body(error_body)}") from exc
        except TimeoutError as exc:
            raise LLMProviderError(f"Gemini API request timed out after {self.timeout_seconds} seconds.") from exc
        except urllib.error.URLError as exc:
            raise LLMProviderError(f"Gemini API request failed: {exc.reason}") from exc

        return self._extract_json(response_body)

    def _should_try_next_key(self, exc: LLMProviderError) -> bool:
        message = str(exc)
        if len(self.api_keys) <= 1:
            return False
        return any(
            marker in message
            for marker in (
                "Gemini API HTTP 400",
                "Gemini API HTTP 401",
                "Gemini API HTTP 403",
                "Gemini API HTTP 429",
                "Gemini API HTTP 500",
                "Gemini API HTTP 502",
                "Gemini API HTTP 503",
                "Gemini API HTTP 504",
            )
        )

    def _sanitize_error_body(self, error_body: str) -> str:
        sanitized = error_body
        for api_key in self.api_keys:
            sanitized = sanitized.replace(api_key, "[redacted]")
        return sanitized

    def _extract_json(self, response_body: str) -> dict[str, Any]:
        try:
            data = json.loads(response_body)
            text = data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise LLMProviderError(f"Unexpected Gemini response shape: {response_body[:500]}") from exc

        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", text, flags=re.DOTALL)
            if not match:
                raise LLMProviderError(f"Gemini did not return JSON: {text[:500]}")
            parsed = json.loads(match.group(0))

        if not isinstance(parsed, dict):
            raise LLMProviderError("Gemini JSON response must be an object")
        return parsed


def build_llm_provider() -> LLMProvider:
    return GeminiLLMProvider()
