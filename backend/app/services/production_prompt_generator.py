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
from app.services.intelligence_context import compact_intelligence_context
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
        data = self._coerce_response(data, variant)
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
        expected_scene_count = len(variant.storyboard)
        if len(package.production_scenes) != expected_scene_count:
            raise ValueError(f"Gemini production package must include exactly {expected_scene_count} production scenes")
        self._validate_production_scenes(package.production_scenes)
        return package

    def _coerce_response(self, data: dict[str, Any], variant: Variant) -> dict[str, Any]:
        scenes = data.get("production_scenes")
        if not isinstance(scenes, list):
            raise ValueError("Gemini production package response must include production_scenes")

        expected_scene_count = len(variant.storyboard)
        data["production_scenes"] = [
            self._coerce_scene(scene, index, variant.storyboard[index - 1] if index - 1 < len(variant.storyboard) else None)
            for index, scene in enumerate(scenes[:expected_scene_count], start=1)
        ]
        if len(data["production_scenes"]) != expected_scene_count:
            raise ValueError(f"Gemini production package must include exactly {expected_scene_count} production scenes")
        self._apply_global_overlay_timeline(data["production_scenes"])

        edit_plan = data.get("edit_plan")
        if not isinstance(edit_plan, dict):
            edit_plan = {}
        cut_sequence = edit_plan.get("cut_sequence")
        if isinstance(cut_sequence, list):
            edit_plan["cut_sequence"] = [self._stringify_item(item) for item in cut_sequence if self._stringify_item(item)]
        else:
            edit_plan["cut_sequence"] = [f"Scene {scene['scene_number']}: {scene['transition']}" for scene in data["production_scenes"]]
        edit_plan["export_ratios"] = self._string_list(edit_plan.get("export_ratios")) or ["9:16", "1:1"]
        edit_plan["required_post_production_steps"] = self._string_list(edit_plan.get("required_post_production_steps"))
        edit_plan.setdefault("total_duration", variant.duration)
        edit_plan.setdefault("pacing_notes", "Short-form UGC pacing with a fast hook, clear demo, and concise CTA.")
        edit_plan.setdefault("music_direction", "Light native social background music under voiceover.")
        edit_plan.setdefault("subtitle_style", "Readable high-contrast captions added in post-production.")
        edit_plan.setdefault("platform_notes", "Export for vertical short-form placement.")
        data["edit_plan"] = edit_plan

        data["asset_checklist"] = self._string_list(data.get("asset_checklist"))
        data["compliance_notes"] = self._string_list(data.get("compliance_notes"))
        data["render_sequence"] = self._string_list(data.get("render_sequence")) or [
            "Generate character reference images.",
            "Generate keyframes per scene.",
            "Animate each keyframe with video prompts.",
            "Add UI overlays, subtitles, logo, disclaimer, and CTA in post-production.",
        ]
        data.setdefault("app_ui_overlay_notes", "Keep app screens clean in generated video and add readable UI overlays in post-production.")
        return data

    def _coerce_scene(self, raw_scene: Any, index: int, storyboard_scene: StoryboardScene | None) -> dict[str, Any]:
        if not isinstance(raw_scene, dict):
            raise ValueError(f"Gemini production scene {index} must be an object")

        scene: dict[str, Any] = dict(raw_scene)
        scene["scene_number"] = self._int_value(scene.get("scene_number"), index)
        scene["duration_seconds"] = self._int_value(
            scene.get("duration_seconds"),
            storyboard_scene.duration_seconds if storyboard_scene else 5,
        )
        if scene["scene_number"] == 3:
            scene["duration_seconds"] = min(scene["duration_seconds"], 6)
        scene.setdefault("creative_objective", scene.get("objective") or (storyboard_scene.objective if storyboard_scene else f"Scene {index}"))
        scene.setdefault("shot_type", scene.get("shot") or "realistic UGC shot")
        scene.setdefault("camera_angle", storyboard_scene.camera_angle if storyboard_scene else "Vertical handheld camera angle")
        scene["generation_mode"] = self._coerce_generation_mode(scene.get("generation_mode"))
        scene["required_reference_assets"] = self._string_list(scene.get("required_reference_assets"))
        scene.setdefault("visual_description", storyboard_scene.visual_description if storyboard_scene else scene["creative_objective"])
        scene.setdefault("action_description", scene.get("action") or scene["visual_description"])
        scene.setdefault("keyframe_prompt", scene.get("image_prompt") or scene.get("prompt") or scene["visual_description"])
        scene.setdefault("video_prompt", scene.get("animation_prompt") or scene.get("motion_prompt") or scene["keyframe_prompt"])
        scene["keyframe_prompt"] = self._sanitize_app_ui_generation_prompt(scene["keyframe_prompt"])
        scene["video_prompt"] = self._sanitize_app_ui_generation_prompt(scene["video_prompt"])
        scene.setdefault("motion_instruction", scene.get("motion") or "Natural subtle UGC movement.")
        scene.setdefault("consistency_instruction", "Preserve the same character identity, outfit, setting, phone, and product props.")
        scene.setdefault("negative_prompt", DEFAULT_PRODUCTION_NEGATIVE_PROMPT)
        scene.setdefault("voiceover_line", storyboard_scene.voiceover_line if storyboard_scene else "")
        scene.setdefault("on_screen_text", storyboard_scene.on_screen_text if storyboard_scene else "")
        scene.setdefault("transition", storyboard_scene.transition if storyboard_scene else "Cut.")
        scene.setdefault("safety_notes", "Use safe claims and keep UI text for post-production overlays.")

        overlays = scene.get("ui_overlay_plan")
        if not isinstance(overlays, list):
            overlays = []
        scene["ui_overlay_plan"] = [
            self._coerce_overlay_item(item, scene["scene_number"], item_index)
            for item_index, item in enumerate(overlays, start=1)
            if isinstance(item, dict)
        ]
        return scene

    def _coerce_overlay_item(self, raw_item: dict[str, Any], scene_number: int, index: int) -> dict[str, str]:
        raw_type = str(raw_item.get("overlay_type") or raw_item.get("type") or "subtitle").lower()
        overlay_type = self._coerce_overlay_type(raw_type)
        text = self._string_value(
            raw_item.get("text")
            or raw_item.get("label")
            or raw_item.get("copy")
            or raw_item.get("content")
            or raw_item.get("button_label")
            or raw_item.get("description")
            or overlay_type.replace("_", " ")
        )
        return {
            "overlay_type": overlay_type,
            "text": text,
            "start_time": self._string_value(raw_item.get("start_time") or raw_item.get("start") or "0:00"),
            "end_time": self._string_value(raw_item.get("end_time") or raw_item.get("end") or "0:03"),
            "position": self._string_value(raw_item.get("position") or raw_item.get("placement") or "center"),
            "style_notes": self._string_value(
                raw_item.get("style_notes")
                or raw_item.get("style")
                or raw_item.get("visual_style")
                or f"Readable {overlay_type} overlay for scene {scene_number}."
            ),
            "safety_notes": self._string_value(
                raw_item.get("safety_notes") or raw_item.get("compliance") or "Keep overlay truthful, readable, and claim-safe."
            ),
        }

    def _coerce_overlay_type(self, raw_type: str) -> str:
        if raw_type == "app_screen":
            return "app_screen_overlay"
        if raw_type in {"app_screen_overlay", "text_overlay", "subtitle", "cta", "disclaimer", "logo", "price_label", "button", "highlight"}:
            return raw_type
        if "cta" in raw_type or "button" in raw_type:
            return "cta"
        if "app" in raw_type or "ui" in raw_type or "screen" in raw_type:
            return "app_screen_overlay"
        if "text" in raw_type or "headline" in raw_type or "hook" in raw_type:
            return "text_overlay"
        if "price" in raw_type or "value" in raw_type:
            return "price_label"
        if "logo" in raw_type or "icon" in raw_type:
            return "logo"
        if "disclaimer" in raw_type:
            return "disclaimer"
        if "highlight" in raw_type:
            return "highlight"
        return "subtitle"

    def _sanitize_app_ui_generation_prompt(self, value: Any) -> str:
        text = self._string_value(value)
        replacements = {
            "app interface clearly visible": "blank clean phone screen reserved for app UI overlay",
            "clearly shows the app interface": "shows a blank clean phone screen reserved for app UI overlay",
            "phone screen clearly shows": "phone screen is blank and reserved for readable UI overlay",
            "displaying the app interface": "with blank clean phone screen for later app UI overlay",
            "readable app text": "no generated app text",
        }
        for source, replacement in replacements.items():
            text = re.sub(re.escape(source), replacement, text, flags=re.IGNORECASE)
        app_terms = ("app", "phone screen", "smartphone", "ui")
        if any(term in text.lower() for term in app_terms) and "later UI overlay" not in text:
            text = f"{text} Phone screen should be blank or clean for later UI overlay. Do not generate readable app text."
        return text

    def _apply_global_overlay_timeline(self, scenes: list[dict[str, Any]]) -> None:
        current_start = 0
        for scene in scenes:
            duration = self._int_value(scene.get("duration_seconds"), 5)
            overlays = scene.get("ui_overlay_plan")
            if isinstance(overlays, list):
                for overlay in overlays:
                    if not isinstance(overlay, dict):
                        continue
                    overlay["start_time"] = self._format_seconds(current_start + self._parse_time_to_seconds(overlay.get("start_time")))
                    overlay["end_time"] = self._format_seconds(current_start + self._parse_time_to_seconds(overlay.get("end_time")))
            current_start += duration

    def _parse_time_to_seconds(self, value: Any) -> int:
        text = str(value or "0").strip()
        if ":" in text:
            parts = text.split(":")
            try:
                return int(parts[-2]) * 60 + int(float(parts[-1]))
            except (ValueError, IndexError):
                return 0
        try:
            return int(float(text.replace("s", "")))
        except ValueError:
            return 0

    def _format_seconds(self, value: int) -> str:
        return f"{value // 60}:{value % 60:02d}"

    def _coerce_generation_mode(self, value: Any) -> str:
        mode = str(value or "image_to_video").lower()
        if mode in {"text_to_image", "image_to_video", "reference_to_video", "overlay_only"}:
            return mode
        if "reference" in mode:
            return "reference_to_video"
        if "text" in mode:
            return "text_to_image"
        if "overlay" in mode:
            return "overlay_only"
        return "image_to_video"

    def _string_list(self, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return [self._stringify_item(item) for item in value if self._stringify_item(item)]
        if isinstance(value, str):
            parts = value.replace("\n", ",").replace(";", ",").split(",")
            return [part.strip() for part in parts if part.strip()]
        return [self._stringify_item(value)]

    def _stringify_item(self, item: Any) -> str:
        if item is None:
            return ""
        if isinstance(item, str):
            return item.strip()
        if isinstance(item, dict):
            return ", ".join(f"{key}: {value}" for key, value in item.items() if value is not None).strip()
        return str(item).strip()

    def _string_value(self, value: Any) -> str:
        return self._stringify_item(value)

    def _int_value(self, value: Any, default: int) -> int:
        try:
            return max(1, int(float(str(value).replace("s", "").strip())))
        except (TypeError, ValueError):
            return default

    def _validate_production_scenes(self, scenes: list[ProductionScene]) -> None:
        for scene in scenes:
            if not scene.keyframe_prompt.strip():
                raise ValueError(f"Production scene {scene.scene_number} is missing keyframe_prompt")
            if not scene.video_prompt.strip():
                raise ValueError(f"Production scene {scene.scene_number} is missing video_prompt")
            is_pov_hand_scene = scene.scene_number == 1 and any(
                token in f"{scene.shot_type} {scene.camera_angle} {scene.visual_description}".lower()
                for token in ("pov", "hand", "hands", "coin close-up")
            )
            has_identity_lock = "Use the same character from the generated character reference images" in scene.video_prompt
            has_hand_lock = "same skin tone" in scene.video_prompt.lower() or "same hand" in scene.video_prompt.lower()
            if not has_identity_lock and not (is_pov_hand_scene and has_hand_lock):
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
        if not isinstance(scenes, list) or not scenes or not isinstance(scenes[-1], dict):
            return

        overlays = scenes[-1].setdefault("ui_overlay_plan", [])
        if not isinstance(overlays, list):
            scenes[-1]["ui_overlay_plan"] = []
            overlays = scenes[-1]["ui_overlay_plan"]

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
            f"Creative / brief context:\n{json.dumps(compact_intelligence_context(product_intelligence), ensure_ascii=False, indent=2)}\n\n"
            f"Variant direction:\n{json.dumps(creative_angle.model_dump(mode='json'), ensure_ascii=False, indent=2)}\n\n"
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
            f"- Create exactly {len(variant.storyboard)} production scenes, matching the storyboard/timeline scene count.\n"
            "- For 4-scene variants: Scene 1 Hook, Scene 2 Problem/Context, Scene 3 Product/Demo, Scene 4 CTA.\n"
            "- For 5-scene variants: Scene 1 Hook, Scene 2 Problem/Context, Scene 3 Product/Demo, Scene 4 Proof/Benefit/Result, Scene 5 CTA.\n"
            "- Each scene must include a keyframe_prompt and video_prompt.\n"
            "- keyframe_prompt is for image generation. video_prompt is for image-to-video/reference-to-video.\n"
            "- Do not write generic prompts like 'user uses the app'.\n"
            "- Describe the character, setting, props, action, camera angle, lighting, emotion, composition, and UI overlay plan.\n"
            f"- Every video_prompt must include this exact identity lock sentence: {character_bible.identity_lock_prompt}\n"
            "- Do not make the video model generate complex readable app UI text.\n"
            "- For phone screens, write: The phone screen should be clean and simple for later UI overlay. Do not generate unreadable app text.\n"
            "- Add real app screenshots only in an app_screen_overlay step. Do not ask the video model to generate app text.\n"
            "- Do not use overlay_type app_screen. Use app_screen_overlay for app UI, text_overlay for hook text, subtitle for captions, cta for CTA, disclaimer for safety copy.\n"
            "- Overlay start_time and end_time should use global final-video timeline, not local scene time.\n"
            "- Use pain_points, demo_moments, proof_points, safe_claims, claims_to_avoid, and creative_angle.\n"
            f"- Always include this negative prompt or a stricter version: {DEFAULT_PRODUCTION_NEGATIVE_PROMPT}\n"
            "- Scene 3 should be 5-6 seconds max. Keep the product/app demo clear and not overloaded with motion.\n"
            "- Scene 1 may be POV/hand-only. If the face is not visible, lock same skin tone and hand style instead of full face/hair identity.\n"
            "- For Coin Scanner App, do not use fortune, guaranteed, 100% accurate, make money, professional appraisal, definitely worth, or extreme values.\n"
            "- For Coin Scanner App, use estimated reference value, reference price, similar coins may have sold for, and actual value may vary disclaimers.\n"
            "- For Coin Scanner App scene 3, use an over-the-shoulder or close-up scanning scene with coin and phone clearly visible.\n"
            "- For Coin Scanner App scene 4, include UI overlays for Estimated Reference Value, Reference price only, Download Now, and Estimated reference value only. Actual value may vary.\n"
        )
