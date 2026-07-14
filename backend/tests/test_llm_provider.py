from typing import Any

import pytest

from app.services.llm_provider import GeminiLLMProvider, LLMProviderError


def test_gemini_timeout_retries_and_can_recover(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = GeminiLLMProvider(
        api_keys=["test-key"],
        timeout_seconds=1,
        transient_max_attempts=2,
        retry_base_seconds=0,
    )
    calls = 0

    def fake_generate(
        api_key: str,
        parts: list[dict[str, Any]],
        *,
        temperature: float,
        response_schema: dict[str, Any] | None,
    ) -> dict[str, Any]:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise LLMProviderError("Gemini API request timed out after 1 seconds.")
        return {"status": "ok"}

    monkeypatch.setattr(provider, "_generate_json_parts_with_key", fake_generate)

    assert provider.generate_json("test") == {"status": "ok"}
    assert calls == 2


def test_gemini_timeout_stops_at_transient_attempt_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = GeminiLLMProvider(
        api_keys=["key-1", "key-2", "key-3"],
        timeout_seconds=1,
        transient_max_attempts=2,
        retry_base_seconds=0,
    )
    attempted_keys: list[str] = []

    def fake_generate(
        api_key: str,
        parts: list[dict[str, Any]],
        *,
        temperature: float,
        response_schema: dict[str, Any] | None,
    ) -> dict[str, Any]:
        attempted_keys.append(api_key)
        raise LLMProviderError("Gemini API request timed out after 1 seconds.")

    monkeypatch.setattr(provider, "_generate_json_parts_with_key", fake_generate)

    with pytest.raises(LLMProviderError, match=r"failed after 2 attempt\(s\)"):
        provider.generate_json("test")

    assert attempted_keys == ["key-1", "key-2"]
