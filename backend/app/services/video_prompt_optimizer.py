import json
from typing import Protocol

from app.models.schemas import OptimizedVideoPrompt, StoryboardScene
from app.services.llm_provider import LLMProvider, build_llm_provider


class VideoPromptOptimizer(Protocol):
    def optimize(
        self,
        scene: StoryboardScene,
        character_reference: str | None = None,
        brand_style: str | None = None,
    ) -> OptimizedVideoPrompt:
        ...


class GeminiVideoPromptOptimizer:
    def __init__(self, llm_provider: LLMProvider | None = None) -> None:
        self.llm_provider = llm_provider or build_llm_provider()

    def optimize(
        self,
        scene: StoryboardScene,
        character_reference: str | None = None,
        brand_style: str | None = None,
    ) -> OptimizedVideoPrompt:
        payload = {
            "scene": scene.model_dump(mode="json"),
            "character_reference": character_reference,
            "brand_style": brand_style,
            "required_output_schema": {
                "video_prompt": "string",
                "negative_prompt": "string",
                "camera_instruction": "string",
                "motion_instruction": "string",
                "consistency_instruction": "string",
                "duration_seconds": 0,
                "aspect_ratio": "9:16",
            },
        }
        prompt = (
            "You are the Video Prompt Optimizer Agent. Rewrite this storyboard scene into a clean, "
            "production-ready video generation prompt. Return JSON only. Keep it realistic and UGC-style "
            "unless brand_style says otherwise. Include character, setting, props, action, camera, lighting, "
            "and emotion. Avoid complex readable UI text; if phone/app UI is needed, keep the screen clean "
            "for later overlay. Include negative prompt coverage for distorted hands, changed face, unreadable "
            "text, extra fingers, wrong product, bad anatomy, flickering, and warped screens.\n\n"
            f"Input:\n{json.dumps(payload, ensure_ascii=False, indent=2)}"
        )
        data = self.llm_provider.generate_json(prompt, temperature=0.35)
        return OptimizedVideoPrompt.model_validate(data)
