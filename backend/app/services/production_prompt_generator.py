import json
import re
from typing import Any

from app.models.schemas import (
    CharacterBible,
    CharacterPlan,
    CharacterReferencePrompt,
    CreativeAngle,
    ProductIntelligenceBrief,
    ProductionScene,
    Project,
    StoryboardScene,
    VideoProductionPackage,
    Variant,
)
from app.services.llm_provider import LLMProvider, build_llm_provider


DEFAULT_PRODUCTION_NEGATIVE_PROMPT = (
    "different person, changed face, different hairstyle, different shirt, older man, younger man, "
    "distorted hands, extra fingers, missing fingers, deformed phone, unreadable text, fake UI text, "
    "random logo, bad anatomy, blurry face, low quality, identity change, face morphing, plastic skin, "
    "cartoon, anime, over-polished commercial look, unrealistic expression"
)

COIN_BANNED_REPLACEMENTS = {
    "guaranteed value": "estimated reference value",
    "100% accurate": "reference-only",
    "100 percent accurate": "reference-only",
    "make money": "learn more about the coin",
    "professional appraisal": "reference estimate",
    "definitely worth": "may have a reference value of",
    "fortune": "interesting find",
}


class GeminiProductionPromptGenerator:
    def __init__(self, llm_provider: LLMProvider | None = None) -> None:
        self.llm_provider = llm_provider or build_llm_provider()

    def generate(
        self,
        *,
        project: Project,
        product_intelligence: ProductIntelligenceBrief,
        creative_angle: CreativeAngle,
        variant: Variant,
        character_plan: CharacterPlan,
        character_bible: CharacterBible,
        character_reference_prompts: list[CharacterReferencePrompt],
    ) -> VideoProductionPackage:
        prompt = self._build_prompt(
            project,
            product_intelligence,
            creative_angle,
            variant,
            character_bible,
            character_reference_prompts,
        )
        data = self.llm_provider.generate_json(prompt, temperature=0.4)
        data = self._sanitize_for_compliance(data, project, product_intelligence)

        package_data = {
            "variant_id": variant.id,
            "creative_angle_id": creative_angle.id,
            "character_plan": character_plan.model_dump(mode="json"),
            "character_bible": character_bible.model_dump(mode="json"),
            "character_reference_prompts": [item.model_dump(mode="json") for item in character_reference_prompts],
            "production_scenes": data.get("production_scenes"),
            "edit_plan": data.get("edit_plan"),
            "app_ui_overlay_notes": data.get("app_ui_overlay_notes"),
            "asset_checklist": data.get("asset_checklist"),
            "compliance_notes": data.get("compliance_notes"),
            "render_sequence": data.get("render_sequence"),
        }
        package = VideoProductionPackage.model_validate(package_data)
        if len(package.production_scenes) != 4:
            raise ValueError("Gemini production package must include exactly 4 production scenes")
        self._validate_production_scenes(package.production_scenes)
        return package

    def _validate_production_scenes(self, scenes: list[ProductionScene]) -> None:
        for scene in scenes:
            if not scene.keyframe_prompt.strip():
                raise ValueError(f"Production scene {scene.scene_number} is missing keyframe_prompt")
            if not scene.video_prompt.strip():
                raise ValueError(f"Production scene {scene.scene_number} is missing video_prompt")
            if "Use the same character from the generated character reference images" not in scene.video_prompt:
                raise ValueError(f"Production scene {scene.scene_number} video_prompt is missing identity lock")

    def _sanitize_for_compliance(
        self,
        data: dict[str, Any],
        project: Project,
        product_intelligence: ProductIntelligenceBrief,
    ) -> dict[str, Any]:
        if not self._is_coin_scanner(project, product_intelligence):
            return data

        sanitized = self._replace_banned_text(data)
        sanitized.setdefault("compliance_notes", [])
        if isinstance(sanitized["compliance_notes"], list):
            sanitized["compliance_notes"].append(
                "Coin value language sanitized to estimated reference value only. Actual value may vary by condition, rarity, and market demand."
            )
        self._ensure_coin_disclaimer(sanitized)
        return sanitized

    def _replace_banned_text(self, value: Any) -> Any:
        if isinstance(value, dict):
            return {key: self._replace_banned_text(item) for key, item in value.items()}
        if isinstance(value, list):
            return [self._replace_banned_text(item) for item in value]
        if not isinstance(value, str):
            return value

        text = value
        for banned, replacement in COIN_BANNED_REPLACEMENTS.items():
            text = re.sub(re.escape(banned), replacement, text, flags=re.IGNORECASE)
        text = re.sub(r"\$\s?\d{1,3}(?:,\d{3})+(?:\s*-\s*\$\s?\d{1,3}(?:,\d{3})+)?", "Estimated Reference Value range", text)
        return text

    def _ensure_coin_disclaimer(self, data: dict[str, Any]) -> None:
        scenes = data.get("production_scenes")
        if not isinstance(scenes, list) or len(scenes) < 4 or not isinstance(scenes[3], dict):
            return

        overlays = scenes[3].setdefault("ui_overlay_plan", [])
        if not isinstance(overlays, list):
            scenes[3]["ui_overlay_plan"] = []
            overlays = scenes[3]["ui_overlay_plan"]

        disclaimer_text = "Estimated reference value only. Actual value may vary."
        has_disclaimer = any(isinstance(item, dict) and disclaimer_text.lower() in str(item.get("text", "")).lower() for item in overlays)
        if not has_disclaimer:
            overlays.append(
                {
                    "overlay_type": "disclaimer",
                    "text": disclaimer_text,
                    "start_time": "0:03",
                    "end_time": "0:05",
                    "position": "bottom",
                    "style_notes": "Small readable caption, high contrast, not distracting from CTA.",
                    "safety_notes": "Required value disclaimer for coin reference estimates.",
                }
            )

    def _is_coin_scanner(self, project: Project, product_intelligence: ProductIntelligenceBrief) -> bool:
        haystack = " ".join(
            [
                project.product_name,
                project.product_category or "",
                project.product_description or "",
                product_intelligence.detected_product,
                product_intelligence.core_use_case,
            ]
        ).lower()
        return "coin" in haystack and ("scan" in haystack or "value" in haystack)

    def _build_prompt(
        self,
        project: Project,
        product_intelligence: ProductIntelligenceBrief,
        creative_angle: CreativeAngle,
        variant: Variant,
        character_bible: CharacterBible,
        character_reference_prompts: list[CharacterReferencePrompt],
    ) -> str:
        brand = {
            "product_name": project.product_name,
            "brand_colors": project.brand_colors,
            "claims_to_avoid": project.claims_to_avoid,
            "cta": project.cta,
            "uploaded_files": [item.file_name for item in project.uploaded_files],
        }
        return (
            "You are an AI video production director and prompt engineer for short-form UGC ads.\n\n"
            "Your job is not only to write a storyboard. Your job is to create a production-ready video generation package.\n\n"
            f"Product Intelligence:\n{json.dumps(product_intelligence.model_dump(mode='json'), ensure_ascii=False, indent=2)}\n\n"
            f"Creative Angle:\n{json.dumps(creative_angle.model_dump(mode='json'), ensure_ascii=False, indent=2)}\n\n"
            f"Script:\n{variant.script}\n\n"
            f"Storyboard:\n{json.dumps([scene.model_dump(mode='json') for scene in variant.storyboard], ensure_ascii=False, indent=2)}\n\n"
            f"Character Bible:\n{json.dumps(character_bible.model_dump(mode='json'), ensure_ascii=False, indent=2)}\n\n"
            f"Character Reference Prompts:\n{json.dumps([item.model_dump(mode='json') for item in character_reference_prompts], ensure_ascii=False, indent=2)}\n\n"
            f"Platform:\n{project.platform}\n\n"
            f"Tone:\n{project.tone}\n\n"
            f"Brand:\n{json.dumps(brand, ensure_ascii=False, indent=2)}\n\n"
            "Return JSON only:\n"
            "{\n"
            '  "production_scenes": [\n'
            "    {\n"
            '      "scene_number": 1,\n'
            '      "duration_seconds": 4,\n'
            '      "creative_objective": "",\n'
            '      "shot_type": "",\n'
            '      "camera_angle": "",\n'
            '      "generation_mode": "image_to_video",\n'
            '      "required_reference_assets": [],\n'
            '      "visual_description": "",\n'
            '      "action_description": "",\n'
            '      "keyframe_prompt": "",\n'
            '      "video_prompt": "",\n'
            '      "motion_instruction": "",\n'
            '      "consistency_instruction": "",\n'
            '      "negative_prompt": "",\n'
            '      "ui_overlay_plan": [],\n'
            '      "voiceover_line": "",\n'
            '      "on_screen_text": "",\n'
            '      "transition": "",\n'
            '      "safety_notes": ""\n'
            "    }\n"
            "  ],\n"
            '  "edit_plan": {\n'
            '    "total_duration": "",\n'
            '    "pacing_notes": "",\n'
            '    "music_direction": "",\n'
            '    "subtitle_style": "",\n'
            '    "cut_sequence": [],\n'
            '    "export_ratios": ["9:16", "1:1"],\n'
            '    "required_post_production_steps": [],\n'
            '    "platform_notes": ""\n'
            "  },\n"
            '  "app_ui_overlay_notes": "",\n'
            '  "asset_checklist": [],\n'
            '  "compliance_notes": [],\n'
            '  "render_sequence": []\n'
            "}\n\n"
            "Rules:\n"
            "- Create exactly 4 production scenes.\n"
            "- Scene 1 is Hook. Scene 2 is Problem/setup. Scene 3 is Product/app demo/proof. Scene 4 is Result + CTA.\n"
            "- Each scene must include a keyframe_prompt and video_prompt.\n"
            "- keyframe_prompt is for image generation. video_prompt is for image-to-video/reference-to-video.\n"
            "- Do not write generic prompts like 'user uses the app'.\n"
            "- Describe the character, setting, props, action, camera angle, lighting, emotion, composition, and UI overlay plan.\n"
            f"- Every video_prompt must include this exact identity lock sentence: {character_bible.identity_lock_prompt}\n"
            "- Do not make the video model generate complex readable app UI text.\n"
            "- For phone screens, write: The phone screen should be clean and simple for later UI overlay. Do not generate unreadable app text.\n"
            "- Use pain_points, demo_moments, proof_points, safe_claims, claims_to_avoid, and creative_angle.\n"
            f"- Always include this negative prompt or a stricter version: {DEFAULT_PRODUCTION_NEGATIVE_PROMPT}\n"
            "- For Coin Scanner App, do not use fortune, guaranteed, 100% accurate, make money, professional appraisal, definitely worth, or extreme values.\n"
            "- For Coin Scanner App, use estimated reference value, reference price, similar coins may have sold for, and actual value may vary disclaimers.\n"
            "- For Coin Scanner App scene 3, use an over-the-shoulder or close-up scanning scene with coin and phone clearly visible.\n"
            "- For Coin Scanner App scene 4, include UI overlays for Estimated Reference Value, Reference price only, Download Now, and Estimated reference value only. Actual value may vary.\n"
        )
