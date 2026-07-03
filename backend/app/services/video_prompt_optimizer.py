from typing import Protocol

from app.models.schemas import OptimizedVideoPrompt, StoryboardScene


class VideoPromptOptimizer(Protocol):
    def optimize(
        self,
        scene: StoryboardScene,
        character_reference: str | None = None,
        brand_style: str | None = None,
    ) -> OptimizedVideoPrompt:
        ...


class RuleBasedVideoPromptOptimizer:
    def optimize(
        self,
        scene: StoryboardScene,
        character_reference: str | None = None,
        brand_style: str | None = None,
    ) -> OptimizedVideoPrompt:
        style = brand_style or "realistic UGC-style short-form ad"
        character = character_reference or "same creator from previous scenes"
        consistency = (
            f"Keep the creator consistent with this reference: {character}."
            if character_reference
            else "Keep the same creator, product, setting, wardrobe, and lighting consistent across scenes."
        )

        return OptimizedVideoPrompt(
            video_prompt=(
                f"{style}. Scene objective: {scene.objective}. Visual: {scene.visual_description}. "
                f"Action should feel natural and handheld. Keep any phone or app screen clean for later overlay. "
                f"Do not rely on complex readable generated text."
            ),
            negative_prompt=(
                f"{scene.negative_prompt}, distorted hands, changed face, unreadable text, extra fingers, "
                "wrong product, bad anatomy, flickering, warped phone screen"
            ),
            camera_instruction=scene.camera_angle,
            motion_instruction=f"Use simple creator movement and a smooth {scene.transition.lower()}",
            consistency_instruction=consistency,
            duration_seconds=scene.duration_seconds,
            aspect_ratio="9:16",
        )
