import json
import re
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Protocol

from app.config import GEMINI_API_BASE_URL, GEMINI_API_KEY, GEMINI_MODEL


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


class MockLLMProvider:
    @property
    def is_configured(self) -> bool:
        return False

    def generate_json(
        self,
        prompt: str,
        *,
        temperature: float = 0.4,
        response_schema: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return {
            "provider": "mock",
            "prompt_preview": prompt[:240],
            "note": "GEMINI_API_KEY is not configured; rule-based fallback was used.",
        }


class GeminiLLMProvider:
    def __init__(
        self,
        api_key: str = GEMINI_API_KEY,
        model: str = GEMINI_MODEL,
        base_url: str = GEMINI_API_BASE_URL,
        timeout_seconds: int = 45,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)

    def generate_json(
        self,
        prompt: str,
        *,
        temperature: float = 0.4,
        response_schema: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not self.is_configured:
            raise LLMProviderError("GEMINI_API_KEY is not configured")

        url = (
            f"{self.base_url}/models/{urllib.parse.quote(self.model, safe='')}:generateContent"
            f"?key={urllib.parse.quote(self.api_key)}"
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
                    "parts": [{"text": prompt}],
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
            raise LLMProviderError(f"Gemini API HTTP {exc.code}: {error_body}") from exc
        except urllib.error.URLError as exc:
            raise LLMProviderError(f"Gemini API request failed: {exc.reason}") from exc

        return self._extract_json(response_body)

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
    provider = GeminiLLMProvider()
    return provider if provider.is_configured else MockLLMProvider()
