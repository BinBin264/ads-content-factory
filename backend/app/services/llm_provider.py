from typing import Protocol


class LLMProvider(Protocol):
    def generate_json(self, prompt: str) -> dict:
        ...


class MockLLMProvider:
    def generate_json(self, prompt: str) -> dict:
        return {
            "provider": "mock",
            "prompt_preview": prompt[:240],
            "note": "Placeholder for a future real LLM provider.",
        }
