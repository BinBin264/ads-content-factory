import json
import re
from typing import Any

from app.models.schemas import (
    CreativePlan,
    NormalizedBrief,
    Project,
    VisionAnalysis,
)
from app.services.llm_provider import LLMProvider, build_llm_provider


class BriefNormalizer:
    def normalize(self, project: Project, vision: VisionAnalysis) -> NormalizedBrief:
        product_type = self._product_type(project, vision)
        description = project.product_description or f"{project.product_name} product brief."
        if project.brief:
            description = f"{description}\n\nCampaign brief: {project.brief}"
        audience = self._string_list(project.audience) or ["target customers"]
        claims_to_avoid = project.claims_to_avoid
        visual_style = project.tone or vision.detected_visual_style or "natural UGC, realistic, mobile-first"
        if vision.detected_visual_style and vision.detected_visual_style not in visual_style:
            visual_style = f"{visual_style}; detected assets: {vision.detected_visual_style}"

        return NormalizedBrief(
            product_name=project.product_name,
            category=project.product_category or vision.detected_product_type or "general",
            product_type=product_type,
            short_description=description,
            target_audience=audience,
            main_problem="Audience needs a clear, believable reason to care now.",
            main_benefit=description,
            emotional_triggers=[],
            functional_benefits=[description],
            proof_elements=vision.detected_ui_elements + vision.detected_objects,
            safe_claims=[],
            claims_to_avoid=claims_to_avoid,
            recommended_visual_style=visual_style,
            recommended_ad_formats=[project.platform, project.duration],
        )

    def _product_type(self, project: Project, vision: VisionAnalysis) -> str:
        raw = f"{project.product_category or ''} {vision.detected_product_type}".lower().replace("-", "_").replace(" ", "_")
        if "app" in raw or "mobile" in raw or "software" in raw:
            return "mobile_app"
        if "skin" in raw or "beauty" in raw:
            return "skincare"
        if "food" in raw or "drink" in raw or "coffee" in raw or "fnb" in raw:
            return "fnb"
        if "education" in raw or "learning" in raw:
            return "education"
        if "ecommerce" in raw or "e_commerce" in raw or "shop" in raw:
            return "ecommerce"
        return vision.detected_product_type if vision.detected_product_type in {"mobile_app", "skincare", "fnb", "ecommerce", "education"} else "general"

    def _string_list(self, value: str | None) -> list[str]:
        if not value:
            return []
        return [item.strip() for item in value.replace("\n", ",").replace(";", ",").split(",") if item.strip()]


class CreativePlanService:
    RESPONSE_SCHEMA = {
        "type": "object",
        "properties": {
            "productAnalysis": {
                "type": "object",
                "properties": {
                    "productType": {"type": "string"},
                    "visibleElements": {"type": "array", "items": {"type": "string"}},
                    "coreBenefit": {"type": "string"},
                    "brandOrVisualCues": {"type": "array", "items": {"type": "string"}},
                    "doNotAssume": {"type": "array", "items": {"type": "string"}},
                    "productLockPrompt": {"type": "string"},
                },
                "required": ["productType", "visibleElements", "coreBenefit", "brandOrVisualCues", "doNotAssume", "productLockPrompt"],
            },
            "productReferences": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "name": {"type": "string"},
                        "kind": {"type": "string"},
                        "visualDescription": {"type": "string"},
                        "lockPrompt": {"type": "string"},
                        "useWhen": {"type": "string"},
                        "isPrimary": {"type": "boolean"},
                    },
                    "required": ["id", "name", "kind", "visualDescription", "lockPrompt", "useWhen", "isPrimary"],
                },
            },
            "scenes": {
                "type": "array",
                "minItems": 2,
                "maxItems": 8,
                "items": {
                    "type": "object",
                    "properties": {
                        "sceneIndex": {"type": "integer"},
                        "narrativePurpose": {"type": "string"},
                        "title": {"type": "string"},
                        "durationSec": {"type": "integer"},
                        "sceneGoal": {"type": "string"},
                        "visualAction": {"type": "string"},
                        "productMoment": {"type": "string"},
                        "characterAction": {"type": "string"},
                        "locationUse": {"type": "string"},
                        "camera": {
                            "type": "object",
                            "properties": {
                                "selected": {"type": "string"},
                                "shot": {"type": "string"},
                                "movement": {"type": "string"},
                                "composition": {"type": "string"},
                                "alternatives": {"type": "array", "items": {"type": "string"}},
                            },
                            "required": ["selected", "shot", "movement", "composition", "alternatives"],
                        },
                        "voiceLines": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "speaker": {"type": "string"},
                                    "timing": {"type": "string"},
                                    "actionState": {"type": "string"},
                                    "emotion": {"type": "string"},
                                    "delivery": {"type": "string"},
                                    "line": {"type": "string"},
                                },
                                "required": ["speaker", "timing", "actionState", "emotion", "delivery", "line"],
                            },
                        },
                        "ambientAudio": {"type": "string"},
                        "onScreenText": {"type": "string"},
                        "timingBeats": {"type": "array", "items": {"type": "string"}},
                        "keyframePrompts": {
                            "type": "array",
                            "minItems": 1,
                            "maxItems": 3,
                            "items": {
                                "type": "object",
                                "properties": {
                                    "id": {"type": "string"},
                                    "label": {"type": "string"},
                                    "timing": {"type": "string"},
                                    "purpose": {"type": "string"},
                                    "prompt": {"type": "string"},
                                    "productReferenceIds": {"type": "array", "items": {"type": "string"}},
                                },
                                "required": ["id", "label", "timing", "purpose", "prompt", "productReferenceIds"],
                            },
                        },
                        "finalVideoPrompt": {"type": "string"},
                        "negativeRules": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": [
                        "sceneIndex",
                        "narrativePurpose",
                        "title",
                        "durationSec",
                        "sceneGoal",
                        "visualAction",
                        "productMoment",
                        "characterAction",
                        "locationUse",
                        "camera",
                        "voiceLines",
                        "ambientAudio",
                        "onScreenText",
                        "timingBeats",
                        "keyframePrompts",
                        "finalVideoPrompt",
                        "negativeRules",
                    ],
                },
            },
        },
        "required": ["productAnalysis", "productReferences", "scenes"],
    }

    def __init__(
        self,
        llm_provider: LLMProvider | None = None,
    ) -> None:
        self.llm_provider = llm_provider or build_llm_provider()

    def build(self, project: Project, brief: NormalizedBrief, vision: VisionAnalysis) -> CreativePlan:
        prompt = self._build_prompt(project, brief, vision)
        # The storytelling scene schema is intentionally enforced by prompt + Pydantic coercion.
        # Passing the full nested schema to Gemini can exceed the service's schema-state limit.
        data = self.llm_provider.generate_json(prompt, temperature=0.35)
        return CreativePlan.model_validate(self._coerce_plan(data, project, brief, vision))

    def _coerce_plan(self, data: dict[str, Any], project: Project, brief: NormalizedBrief, vision: VisionAnalysis) -> dict[str, Any]:
        product_analysis = data.get("productAnalysis") or data.get("product_analysis")
        scenes = data.get("scenes")
        if isinstance(product_analysis, dict) and isinstance(scenes, list):
            return self._coerce_storytelling_plan(data, project, brief, vision)

            raise ValueError("Plan Creation must include productAnalysis and 2 to 8 scenes.")

    def _coerce_storytelling_plan(self, data: dict[str, Any], project: Project, brief: NormalizedBrief, vision: VisionAnalysis) -> dict[str, Any]:
        product_analysis = data.get("productAnalysis") or data.get("product_analysis") or {}
        product_references = data.get("productReferences") or data.get("product_references") or []
        scenes = data.get("scenes") or []
        if not isinstance(product_analysis, dict):
            raise ValueError("Plan Creation must include productAnalysis.")
        if not isinstance(product_references, list):
            product_references = []
        if not isinstance(scenes, list) or len(scenes) < 2:
            raise ValueError("Plan Creation must include 2 to 8 scenes.")
        scene_limit = self._target_scene_count(project)
        coerced_scenes = self._coerce_four_second_scenes(scenes[:scene_limit])

        return {
            "productAnalysis": product_analysis,
            "productReferences": product_references,
            "scenes": coerced_scenes,
        }

    def _build_prompt(self, project: Project, brief: NormalizedBrief, vision: VisionAnalysis) -> str:
        target_scene_count = self._target_scene_count(project)
        product_context = {
            "project": {
                "product_name": project.product_name,
                "product_category": project.product_category,
                "product_description": project.product_description,
                "audience": project.audience,
                "goal": project.goal,
                "platform": project.platform,
                "duration": project.duration,
                "tone": project.tone,
                "cta": project.cta,
                "claims_to_avoid": project.claims_to_avoid,
            },
            "normalized_brief": brief.model_dump(mode="json"),
            "vision_analysis": vision.model_dump(mode="json"),
        }
        user_brief = project.brief or brief.short_description
        product_references_json = self._product_references_payload(project, vision)
        return (
            "You are an expert direct-response video ads planner.\n\n"
            "Create a short storytelling ad plan from the user's brief and uploaded product reference set. "
            "The output is the main production plan users will copy into image/video tools, so return strict JSON only.\n\n"
            "Inputs:\n"
            f"- Brief: {user_brief}\n"
            f"- Optional product context: {json.dumps(product_context, ensure_ascii=False, indent=2)}\n"
            "- Aspect ratio: 9:16\n"
            "- Voice mode: native_video_audio\n"
            "- Voice language: same language as the user's brief; use Vietnamese if the brief is Vietnamese\n"
            "- Overlay mode: enabled\n"
            "- Scene clip length: 4 seconds exactly\n"
            f"- Target scene count: {target_scene_count} scenes, one 4-second video clip per scene\n"
            f"- Uploaded product references JSON: {json.dumps(product_references_json, ensure_ascii=False, indent=2)}\n\n"
            "Required JSON shape:\n"
            "{\n"
            '  "productAnalysis": {\n'
            '    "productType": "what the references show",\n'
            '    "visibleElements": ["observable details only"],\n'
            '    "coreBenefit": "benefit that can be supported by the brief/context",\n'
            '    "brandOrVisualCues": ["colors, UI, packaging, product traits"],\n'
            '    "doNotAssume": ["claims or details that must not be invented"],\n'
            '    "productLockPrompt": "short rule for preserving product/app appearance"\n'
            "  },\n"
            '  "productReferences": [\n'
            "    {\n"
            '      "id": "use the uploaded product reference id exactly",\n'
            '      "name": "stable human label",\n'
            '      "kind": "app_screen | physical_product | packaging | logo | usage_photo | before_after | other",\n'
            '      "visualDescription": "what this reference image visibly contains",\n'
            '      "lockPrompt": "what must be preserved when this reference is used",\n'
            '      "useWhen": "when this reference is useful in the ad",\n'
            '      "isPrimary": true\n'
            "    }\n"
            "  ],\n"
            '  "scenes": [\n'
            "    {\n"
            '      "sceneIndex": 1,\n'
            '      "narrativePurpose": "hook + product_app_introduction",\n'
            '      "title": "short scene title",\n'
            '      "durationSec": 4,\n'
            '      "sceneGoal": "why this scene exists in the ad",\n'
            '      "visualAction": "one focused 4-second action beat with a clear start and end",\n'
            '      "productMoment": "how the uploaded product/app references are shown inside this 4-second clip",\n'
            '      "characterAction": "what the actor/model does inside this 4-second clip; if a selected actor model is expected, describe the role without inventing a separate character bible",\n'
            '      "locationUse": "how the filming setting appears inside this scene only",\n'
            '      "camera": {"selected": "stable eye-level medium shot", "shot": "medium shot", "movement": "connected camera movement", "composition": "product/app visible and readable at the important moment", "alternatives": ["over-the-shoulder phone close-up"]},\n'
            '      "voiceLines": [{"speaker": "Primary actor", "timing": "0-4s", "actionState": "visible action or state while speaking", "emotion": "natural emotion", "delivery": "voice style in requested language", "line": "exact spoken line"}],\n'
            '      "ambientAudio": "room tone and useful SFX for this video segment",\n'
            '      "onScreenText": "short overlay text only when Overlay mode is enabled; otherwise empty string",\n'
            '      "timingBeats": ["0-2s: ...", "2-4s: ..."],\n'
            '      "keyframePrompts": [{"id": "kf_setup", "label": "Actor and product setup", "timing": "0-2s", "purpose": "product state, actor/model action, setting, and composition this image should contribute to video generation", "prompt": "image generation prompt for this visual ingredient", "productReferenceIds": ["uploaded_product_ref_id"]}],\n'
            '      "finalVideoPrompt": "self-contained video prompt with action, camera, duration, dialogue/audio, locks, reference mapping, overlay intent, and negative rules",\n'
            '      "negativeRules": ["do not redesign the product/app", "no unreadable UI text"]\n'
            "    }\n"
            "  ]\n"
            "}\n\n"
            "Rules:\n"
            "1. Return JSON only, no markdown, no code fence.\n"
            f"2. Generate exactly {target_scene_count} scenes unless the brief is extremely simple. Each scene is one separate 4-second video generation clip.\n"
            "3. Split the story by natural 4-second beats. Do not cram discovery, scanning, result, reaction, and CTA into one clip. Make each clip visually executable by a video model.\n"
            "4. Use storytelling structure across the scene list: hook, product/app introduction, proof/demo, result, CTA. A scene should contain only what can happen clearly in 4 seconds.\n"
            "5. Do not create separate top-level character or location bibles in this phase. Describe actor/model usage and setting only inside each scene.\n"
            "6. Include camera terms for every scene.\n"
            "7. Use structured voiceLines, not one short voiceLine string. A scene may have multiple spoken lines if they fit the continuous action naturally.\n"
            "8. All voiceLines.line values must be written in Voice language unless the brief explicitly asks for a different phrase. Do not add English translations unless visible product/app UI itself contains English.\n"
            "9. Analyze each uploaded product reference independently and preserve its existing id. Do not assume every reference is an app screen. Use only relevant product references for each keyframe prompt.\n"
            "10. Each 4-second scene must have 1 to 2 keyframePrompts. Each prompt must mention product, actor/model action, setting, composition, and camera. If an app screen needs readable UI, at least one relevant keyframe prompt must be a phone/UI close-up or insert shot.\n"
            "11. finalVideoPrompt must be self-contained and must map reference images by keyframe prompt order. Explicitly say reference images are visual ingredients, not an automatic chronological slideshow.\n"
            "12. Every scene durationSec must be exactly 4. Every finalVideoPrompt must explicitly start with or include: Create a 4-second vertical video.\n"
            "13. If Overlay mode is disabled, set onScreenText to an empty string and say No overlay text in finalVideoPrompt. If enabled, onScreenText must be no more than 6 words.\n"
            "14. Keep setting continuity inside scenes, but do not output a separate location bible. Use concise location anchors only when they help the scene prompt.\n"
            "15. JSON SAFETY: never use raw ASCII double quotes inside string values. If quoted speech is needed inside a string value, use corner brackets.\n"
        )

    def _target_scene_count(self, project: Project) -> int:
        duration_text = str(project.duration or "").lower()
        match = re.search(r"\d+", duration_text)
        duration_seconds = int(match.group(0)) if match else 20
        if duration_seconds <= 12:
            return 3
        if duration_seconds <= 16:
            return 4
        if duration_seconds <= 22:
            return 5
        if duration_seconds <= 26:
            return 6
        return 8

    def _coerce_four_second_scenes(self, scenes: list[Any]) -> list[dict[str, Any]]:
        coerced_scenes: list[dict[str, Any]] = []
        for index, raw_scene in enumerate(scenes):
            if not isinstance(raw_scene, dict):
                continue
            scene = dict(raw_scene)
            scene["sceneIndex"] = index + 1
            scene["durationSec"] = 4
            final_prompt = str(scene.get("finalVideoPrompt") or "").strip()
            if final_prompt:
                final_prompt = re.sub(r"\b\d+\s*[- ]seconds?\b", "4-second", final_prompt, flags=re.IGNORECASE)
                if "4-second vertical video" not in final_prompt.lower():
                    final_prompt = f"Create a 4-second vertical video. {final_prompt}"
                scene["finalVideoPrompt"] = final_prompt
            coerced_scenes.append(scene)
        return coerced_scenes

    def _product_references_payload(self, project: Project, vision: VisionAnalysis) -> list[dict[str, Any]]:
        if project.uploaded_files:
            return [
                {
                    "id": item.id,
                    "file_name": item.file_name,
                    "content_type": item.content_type,
                    "url": item.url,
                    "kind_hint": "uploaded_product_reference",
                }
                for item in project.uploaded_files
            ]
        return [
            {
                "id": "vision_summary",
                "file_name": "vision_analysis",
                "content_type": "application/json",
                "kind_hint": "vision_summary",
                "detected_objects": vision.detected_objects,
                "detected_ui_elements": vision.detected_ui_elements,
                "detected_text": vision.detected_text,
                "detected_brand_colors": vision.detected_brand_colors,
            }
        ]

    def _string(self, value: Any) -> str:
        if isinstance(value, list):
            value = " ".join(str(item).strip() for item in value if str(item).strip())
        return str(value or "").strip()

    def _string_list(self, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return [self._string(item) for item in value if self._string(item)]
        return [item.strip() for item in str(value).replace("\n", ",").replace(";", ",").split(",") if item.strip()]
