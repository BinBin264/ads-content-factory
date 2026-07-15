import base64
import json
import re
from pathlib import Path
from typing import Any

from app.models.schemas import (
    CreativePlan,
    NormalizedBrief,
    Project,
    VisionAnalysis,
)
from app.services.llm_provider import LLMProvider, build_llm_provider
from app.services.production_orchestrator import ProductionOrchestrator


DEFAULT_SCENE_CLIP_SECONDS = 8
ALLOWED_SCENE_CLIP_SECONDS = (4, 6, 8, 10)
KEYFRAMES_PER_SCENE = 1
NATIVE_DIALOGUE_WORDS_PER_SECOND = 2.0


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
            "primaryCharacter": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "description": {"type": "string"},
                    "imagePrompt": {"type": "string"},
                    "consistencyPrompt": {"type": "string"},
                },
                "required": ["name", "description", "imagePrompt", "consistencyPrompt"],
            },
            "primaryLocation": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "description": {"type": "string"},
                    "imagePrompt": {"type": "string"},
                    "consistencyPrompt": {"type": "string"},
                },
                "required": ["name", "description", "imagePrompt", "consistencyPrompt"],
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
                        "openingState": {"type": "string"},
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
                                    "generationMode": {"type": "string"},
                                },
                                "required": ["speaker", "timing", "actionState", "emotion", "delivery", "line", "generationMode"],
                            },
                        },
                        "ambientAudio": {"type": "string"},
                        "onScreenText": {"type": "string"},
                        "timingBeats": {"type": "array", "items": {"type": "string"}},
                        "keyframePrompts": {
                            "type": "array",
                            "minItems": 1,
                            "maxItems": 1,
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
                        "openingState",
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
        "required": ["productAnalysis", "productReferences", "primaryCharacter", "primaryLocation", "scenes"],
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
        data = self.llm_provider.generate_json_parts(self._build_parts(project, prompt), temperature=0.35)
        plan = CreativePlan.model_validate(self._coerce_plan(data, project, brief, vision))
        return ProductionOrchestrator().prepare_plan(project, plan)

    def _build_parts(self, project: Project, prompt: str) -> list[dict[str, Any]]:
        parts: list[dict[str, Any]] = [{"text": prompt}]
        image_index = 0
        for uploaded_file in project.uploaded_files:
            if not uploaded_file.content_type or not uploaded_file.content_type.startswith("image/"):
                continue
            path = Path(uploaded_file.path)
            if not path.exists():
                continue
            image_index += 1
            parts.append({"text": f"\n\nUploaded product reference {image_index}: {uploaded_file.id} - {uploaded_file.file_name}\n"})
            parts.append(
                {
                    "inlineData": {
                        "mimeType": uploaded_file.content_type,
                        "data": base64.b64encode(path.read_bytes()).decode("ascii"),
                    }
                }
            )
        return parts

    def _coerce_plan(self, data: dict[str, Any], project: Project, brief: NormalizedBrief, vision: VisionAnalysis) -> dict[str, Any]:
        product_analysis = data.get("productAnalysis") or data.get("product_analysis")
        scenes = data.get("scenes")
        if isinstance(product_analysis, dict) and isinstance(scenes, list):
            return self._coerce_storytelling_plan(data, project, brief, vision)

        raise ValueError("Plan Creation must include productAnalysis and 2 to 8 scenes.")

    def _coerce_storytelling_plan(self, data: dict[str, Any], project: Project, brief: NormalizedBrief, vision: VisionAnalysis) -> dict[str, Any]:
        product_analysis = data.get("productAnalysis") or data.get("product_analysis") or {}
        product_references = data.get("productReferences") or data.get("product_references") or []
        primary_character = data.get("primaryCharacter") or data.get("primary_character") or {}
        primary_location = data.get("primaryLocation") or data.get("primary_location") or {}
        scenes = data.get("scenes") or []
        if not isinstance(product_analysis, dict):
            raise ValueError("Plan Creation must include productAnalysis.")
        if not isinstance(product_references, list):
            product_references = []
        if not isinstance(scenes, list) or len(scenes) < 2:
            raise ValueError("Plan Creation must include 2 to 8 scenes.")
        scene_limit = self._target_scene_count(project)
        coerced_product_references = self._coerce_product_references(product_references, project, vision)
        coerced_scenes = self._coerce_scene_clips(scenes[:scene_limit], coerced_product_references)

        return {
            "productAnalysis": product_analysis,
            "productReferences": coerced_product_references,
            "primaryCharacter": self._coerce_primary_character(primary_character, project, brief),
            "primaryLocation": self._coerce_primary_location(primary_location, project, brief),
            "storySpine": data.get("storySpine") if isinstance(data.get("storySpine"), dict) else {},
            "worldBible": data.get("worldBible") if isinstance(data.get("worldBible"), dict) else {},
            "safetyPlan": data.get("safetyPlan") if isinstance(data.get("safetyPlan"), dict) else {},
            "scenes": coerced_scenes,
        }

    def _build_prompt(self, project: Project, brief: NormalizedBrief, vision: VisionAnalysis) -> str:
        target_scene_count = self._target_scene_count(project)
        is_content_creation = project.workflow_type == "content_creation"
        planner_role = (
            "You are an expert AI video content production planner."
            if is_content_creation
            else "You are an expert direct-response video ads planner."
        )
        planning_task = (
            "Create a short content video production plan from the user's idea and uploaded visual reference set. "
            if is_content_creation
            else "Create a short storytelling ad plan from the user's brief and uploaded product reference set. "
        )
        workflow_note = (
            "- Workflow type: content_creation. This is not necessarily an ad. Treat product_name as the content title or concept name. "
            "Do not force a CTA, product proof, app demo, purchase logic, or direct-response structure unless the user explicitly asks for it. "
            "Use uploaded files as optional visual references for characters, props, places, style, or objects.\n"
            if is_content_creation
            else "- Workflow type: video_ads. Optimize for a product/app ad with clear hook, problem, demo/proof, result, and CTA when relevant.\n"
        )
        structure_rule = (
            "4. Use a content creation structure across the scene list: hook/opening image, setup, visual development, payoff, ending beat. "
            "Do not force product proof, purchase, app demo, or CTA unless the user requested those. If the idea is cinematic, educational, vlog, skit, or story content, preserve that format.\n"
            if is_content_creation
            else "4. Use storytelling structure across the scene list: hook, setup, product/app introduction, proof/demo, result/reaction, CTA. Do not compress discovery, scan, result, reaction, payment, and CTA into one scene if they can be separated into clearer keyframes.\n"
        )
        reference_policy = (
            "- Visual reference policy: each keyframe may use zero or one uploaded visual reference and only the minimum canonical character/location reference needed for that shot. "
            "Do not attach all references by default. If a scene needs multiple distinct visual states, split those into separate scenes/keyframes.\n"
            if is_content_creation
            else "- Product/app reference policy: each keyframe may use zero or one uploaded product/app reference and only the minimum canonical character/location reference needed for that shot. "
            "Do not attach all references or multiple app screens to one keyframe. If a scene needs the home screen, scan screen, and result screen, split those into separate scenes/keyframes.\n"
        )
        reference_rule = (
            "9. Visual reference handling: analyze each uploaded reference independently and preserve its existing id. Preserve each uploaded file_name or stable uploaded name exactly in productReferences.name when available. Use only the one relevant visual reference for each keyframe prompt, or use none if no uploaded reference is visibly needed. Do not dump every reference into every keyframe prompt.\n"
            if is_content_creation
            else "9. Product reference handling: analyze each uploaded product reference independently and preserve its existing id. Preserve each uploaded file_name or stable uploaded name exactly in productReferences.name when available. Do not assume every reference is an app screen. Use only the one relevant product reference for each keyframe prompt, or use none if the uploaded product/app is not visibly shown. Do not dump every product reference into every keyframe prompt.\n"
        )
        reference_json_label = "Uploaded visual references JSON" if is_content_creation else "Uploaded product references JSON"
        product_context = {
            "project": {
                "workflow_type": project.workflow_type,
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
            f"{planner_role}\n\n"
            f"{planning_task}"
            "The output is the main production plan users will copy into image/video tools, so return strict JSON only.\n\n"
            "Inputs:\n"
            f"- Brief: {user_brief}\n"
            f"- Optional product context: {json.dumps(product_context, ensure_ascii=False, indent=2)}\n"
            f"{workflow_note}"
            "- The brief may contain a user script/timeline, character brief, location brief, target duration, spoken lines, subtitles, translations, or notes. Treat those as user constraints when present.\n"
            "- Aspect ratio: 9:16. This is a provider parameter; do not repeat aspect ratio or vertical format inside finalVideoPrompt.\n"
            "- Voice mode: hybrid. Use native video speech only when one short line fits naturally; otherwise preserve the exact line as post_voiceover and generate ambience only in the video model.\n"
            "- Planning/output language: English for scene titles, scene goals, keyframe prompts, final video prompts, product locks, and production instructions unless the user explicitly asks the whole plan to be in another language.\n"
            "- Voice language: use the exact dialogue language requested in the brief only for voiceLines.line and onScreenText when relevant. Preserve user-supplied spoken lines exactly. If the brief includes Spanish dialogue snippets, keep those snippets in Spanish but do not translate the entire plan into Spanish.\n"
            "- Overlay mode: enabled\n"
            f"- Scene clip duration options: {', '.join(str(item) + 's' for item in ALLOWED_SCENE_CLIP_SECONDS)}. Choose durationSec per scene based on action complexity. This is a provider parameter; do not repeat clip duration inside finalVideoPrompt.\n"
            f"- Target scene count: {target_scene_count} scenes, one video clip per scene\n"
            f"- Keyframes per scene: exactly {KEYFRAMES_PER_SCENE}. Use the keyframe as the single visual anchor for that clip.\n"
            f"{reference_policy}"
            f"- {reference_json_label}: {json.dumps(product_references_json, ensure_ascii=False, indent=2)}\n\n"
            "Required JSON shape:\n"
            "{\n"
            '  "storySpine": {"logline": "one-sentence story", "storyPromise": "what the audience expects", "objective": "production objective", "initialCondition": "visible opening state", "finalOutcome": "visible final state", "tone": "consistent tone"},\n'
            '  "worldBible": {"visualGrammar": "project-wide camera and composition rules", "lightingContinuity": "motivated light direction and color relationship", "atmosphereContinuity": "recurring environmental and audio cues"},\n'
            '  "safetyPlan": {"claimsToAvoid": ["unsupported claims"], "referencePolicy": "authorized-reference rule", "rewriteRules": ["safe original alternative when a protected identity or style cannot be used"]},\n'
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
            '      "name": "use the uploaded product reference file_name or stable uploaded name exactly when available",\n'
            '      "kind": "app_screen | physical_product | packaging | logo | usage_photo | before_after | other",\n'
            '      "visualDescription": "what this reference image visibly contains",\n'
            '      "lockPrompt": "what must be preserved when this reference is used",\n'
            '      "useWhen": "when this reference is useful in the ad",\n'
            '      "isPrimary": true\n'
            "    }\n"
            "  ],\n"
            '  "primaryCharacter": {\n'
            '    "name": "Primary actor",\n'
            '    "description": "single consistent actor description suitable for ads",\n'
            '    "imagePrompt": "prompt to generate one clean reference image containing exactly one actor on a neutral background with relaxed hands and no props",\n'
            '    "consistencyPrompt": "identity lock text for later keyframes"\n'
            "  },\n"
            '  "primaryLocation": {\n'
            '    "name": "Primary setting",\n'
            '    "description": "single consistent environment description with cinematic mood plus concise recurring props and layout anchors",\n'
            '    "imagePrompt": "prompt to generate one attractive cinematic location reference image with no primary actor; background extras only when necessary and with indistinct unrelated faces; use a natural three-quarter commercial view with recurring props",\n'
            '    "consistencyPrompt": "location lock text for later keyframes: fixed layout, prop relationships, window/light direction, background anchors, and how props should appear from same, side, top-down, or opposite camera angles"\n'
            "  },\n"
            '  "scenes": [\n'
            "    {\n"
            '      "sceneIndex": 1,\n'
            '      "narrativePurpose": "hook + product_app_introduction",\n'
            '      "title": "short scene title",\n'
            f'      "durationSec": {DEFAULT_SCENE_CLIP_SECONDS},\n'
            '      "sceneGoal": "why this scene exists in the ad",\n'
            '      "openingState": "the frozen visible state at frame 0 immediately before this scene action starts; no result or completed action",\n'
            '      "dramaticFunction": "introduce | deepen | turn | payoff",\n'
            '      "arcPosition": "open | rising | turn | climax | release",\n'
            '      "direction": {"valueShift": "visible before-to-after shift", "feltIntent": "what the viewer should feel or notice", "lighting": "motivated lighting choice serving that intent", "atmosphere": "environment and sound density serving that intent", "performanceSubtext": "truth expressed through one visible behavior"},\n'
            '      "visualAction": "one simple motion delta that begins after openingState and ends at one visible outcome",\n'
            '      "productMoment": "how the uploaded product/app references are shown inside this clip without redesigning them; mention @suggested_reference_label or @file_name when a product reference is visible",\n'
            '      "characterAction": "what the primary character does inside this clip, including visible facial expression, body language, hands, and gaze",\n'
            '      "locationUse": "how the primary location appears inside this clip, including camera viewpoint relative to the location reference",\n'
            '      "camera": {"selected": "stable eye-level medium shot", "shot": "medium shot", "movement": "connected camera movement", "composition": "product/app visible and readable at the important moment", "alternatives": ["over-the-shoulder phone close-up"]},\n'
            '      "voiceLines": [{"speaker": "Primary actor", "timing": "0-[durationSec]s", "actionState": "visible action or state while speaking", "emotion": "natural emotion", "delivery": "voice style in requested language", "line": "exact spoken line", "generationMode": "native | post_voiceover"}],\n'
            '      "ambientAudio": "room tone and useful SFX for this video segment",\n'
            '      "onScreenText": "short overlay text only when Overlay mode is enabled; otherwise empty string",\n'
            '      "timingBeats": ["0-2s: ...", "2-[durationSec]s: ..."],\n'
            f'      "keyframePrompts": [{{"id": "kf_main", "label": "Opening keyframe", "timing": "0s", "purpose": "frame 0 before the scene action: one actor instance, one simple stable pose, explicit hand/prop ownership, one product/app state, fixed location viewpoint, and no completed outcome", "prompt": "still-image prompt showing openingState only; preserve references exactly, mention at most one visible product reference as @suggested_reference_label or @file_name, and reserve visualAction for video motion", "productReferenceIds": ["zero_or_one_uploaded_product_ref_id"]}}],\n'
            '      "finalVideoPrompt": "motion-only video prompt that treats the keyframe as frame 0, advances one action to one endpoint, uses one camera move, contains only active native dialogue or a no-speech/post_voiceover instruction, and never repeats static source details",\n'
            '      "negativeRules": ["do not redesign the product/app", "no unreadable UI text"]\n'
            "    }\n"
            "  ]\n"
            "}\n\n"
            "Rules:\n"
            "1. Return JSON only, no markdown, no code fence.\n"
            f"2. Generate exactly {target_scene_count} scenes. Ignore the user's requested duration when deciding scene count; optimize for controllable keyframe quality and manual review.\n"
            "3. Split the story into clear visual production units. Prefer more small scenes over fewer abstract scenes. Each scene should be one concrete visual beat that can be judged from one generated keyframe before creating video.\n"
            "3a. Every scene must have one dramatic function, one visible value shift, one felt intent, one primary generation spend, and one changed endpoint. If a scene asks for several major actions, locations, product states, or story turns, split it into more scenes.\n"
            "3b. Direct from intention rather than generic adjectives. Camera, blocking, performance, motivated lighting, atmosphere, and sound must all serve the same feltIntent. Do not use cinematic, epic, or beautiful as substitutes for concrete direction.\n"
            f"{structure_rule}"
            "5. Use one primaryCharacter and one primaryLocation. They are first-class reference-image prompts for the next production step. If the brief includes character or location instructions, primaryCharacter and primaryLocation must follow them.\n"
            "6. Include camera terms for every scene.\n"
            "7. Use structured voiceLines, not one short voiceLine string. Budget native speech at no more than about 2 words per second and one speaker/line per generated clip. If exact dialogue exceeds that budget or multiple lines must be preserved, set generationMode to post_voiceover instead of forcing rushed native speech.\n"
            "8. Voice handling: all production planning fields must stay in Planning/output language. voiceLines.line may use the requested dialogue language from the brief. Treat quoted spoken dialogue in the brief as spoken line exactly. Do not paraphrase, translate, shorten, soften, or rewrite spoken lines. Text marked as subtitles, translations, Vietsub, notes, or parenthetical non-spoken explanations is not spoken unless the user explicitly says it should be spoken. Each spoken sentence belongs to one scene only; never repeat a previous scene's line in a later scene.\n"
            f"{reference_rule}"
            "9a. For each uploaded product reference, keep sourceFileName and referenceLabel aligned with the real uploaded file so the user can match the plan back to the uploaded image. Do not invent unrelated reference names.\n"
            "9b. productReferenceIds must contain at most one id. Use [] for actor-only, location-only, coin-only, reaction, payment, or CTA shots where the uploaded app/product UI is not visible and readable. A phone as a prop is not enough to attach an app-screen reference; attach an app reference only when the screen content should be preserved.\n"
            "9c. For app references, choose exactly one screen state per keyframe: home/start screen OR scan/camera screen OR result/detail/price screen. Never combine home, scan, and result screenshots in the same keyframe prompt.\n"
            "9d. Assign every reference one role and an exclusion boundary. Character references carry identity and wardrobe only; location references carry environment geometry and light direction only; product references carry exact product or UI appearance only. Never let one reference overwrite unrelated identity, location, camera, motion, or audio.\n"
            "10. Each scene must have exactly 1 keyframePrompts item with id kf_main. It is frame 0 immediately BEFORE visualAction starts, never a summary or the scene endpoint. The attached keyframe carries static state; the video prompt carries only the motion delta. If the keyframe would be hard to judge, split the story into another scene instead of adding more keyframes inside the same scene.\n"
            "10a. Keyframe prompts and finalVideoPrompt must preserve uploaded product/app/user references exactly: do not redesign UI layout, text, colors, packaging, product shape, coin details, logo, actor identity, outfit, location layout, or any user-provided visual reference. If the scene needs readable UI or readable text, the relevant keyframe prompt must make the phone/UI/product reference large enough and angled for readability, not a tiny background prop.\n"
            "10b. Never write internal file ids like file_xxx inside keyframe prompt text or finalVideoPrompt. Use @suggested_reference_label or @file_name in human-readable prompt text, while productReferenceIds keeps the exact uploaded reference id.\n"
            "10c. When an actor is present, openingState and the keyframe prompt must define one frozen pose: facial expression, body posture, gaze, and explicit prop ownership. Keep both hands anatomically simple. Never ask the still image to show tapping, grabbing, passing, pocketing, turning, pointing, and reacting simultaneously.\n"
            "10d. The keyframe must show the exact opening state the video should preserve: exactly one primary actor instance, face, outfit, left/right orientation, hand position, one product/app state, location geometry, lighting direction, camera viewpoint, and any selected readable UI detail. Background extras must not copy the primary actor's face or outfit.\n"
            "10e. Reference allocation is a fidelity budget. For a product/UI close-up, use only that one product reference unless the actor's face must be visible. For an actor-plus-product shot, use product plus character and carry location through text. For an actor-only shot, use character plus location. Never use all references by default.\n"
            "11. finalVideoPrompt must treat the selected keyframe as frame 0 and the sole visual source of truth. Do not re-describe static details already visible. Include only the current motion delta, one motivated camera move, active native dialogue or an explicit post_voiceover/no-speech instruction, ambient audio, one endpoint, future-beat exclusions, and preservation rules. Explicitly forbid replaying the opening action, restarting previous dialogue, duplicating the actor, mirroring handedness, or changing prop ownership.\n"
            "12. Choose durationSec from exactly one of 4, 6, 8, or 10. Use 4s for one simple motion, 6s for one action plus a small reaction, 8s for two tightly connected motions or a product demo, and 10s only when the continuous physical action needs it. Long narration is post_voiceover, not a reason to overload native video speech. finalVideoPrompt must NOT mention duration, seconds, vertical format, portrait mode, or 9:16 because those are provider parameters.\n"
            "13. If Overlay mode is disabled, set onScreenText to an empty string and say No overlay text in finalVideoPrompt. If enabled, onScreenText must be no more than 6 words.\n"
            "14. primaryLocation.imagePrompt must create a natural, attractive commercial reference image with depth, motivated lighting, and a usable filming surface. It must not contain the primary actor. Any necessary background extras have indistinct faces and must look different from the primary actor. Its consistencyPrompt must define fixed world-space layout, recurring props, physical relationships, window/light direction, background anchors, and the chosen reference view.\n"
            "14a. Each keyframe prompt must state the camera viewpoint relative to the location reference: same reference view, left side angle, right side angle, top-down view, or opposite side view. If a scene uses an opposite or side angle, explicitly say it is the same fixed layout viewed from that new angle.\n"
            "14b. Smooth scene continuity: each scene's main keyframe should visually hand off from the previous scene and into the next scene through matching actor posture, screen/product state, gaze direction, hand position, camera angle, or motion direction. Avoid hard resets unless the brief needs a deliberate cut.\n"
            "14c. Treat each generated scene as an intentional editorial shot opened from canonical references. Do not build an unlimited output-to-output chain. Accepted footage may inform the next scene's opening state, but character, wardrobe, product geometry, location layout, and style must re-anchor from the canonical references.\n"
            "14d. Put subtitles, precise CTA copy, prices, disclaimers, and small readable text in post-production. Do not spend generation fidelity trying to render them inside moving footage.\n"
            "14e. Prefer original, authorized characters and references. Do not imitate a real private person, celebrity, protected character, artist style, logo, voice, or copyrighted performance unless the brief clearly establishes authorization; rewrite to a generic original alternative instead of attempting to bypass provider safeguards.\n"
            "15. JSON SAFETY: never use raw ASCII double quotes inside string values. If quoted speech is needed inside a string value, use corner brackets.\n"
        )

    def _coerce_primary_character(self, value: Any, project: Project, brief: NormalizedBrief) -> dict[str, Any]:
        character = value if isinstance(value, dict) else {}
        description = self._string(character.get("description")) or "Single consistent commercial actor for this ad."
        image_prompt = self._string(character.get("imagePrompt")) or (
            f"Realistic commercial actor reference for {project.product_name}. "
            f"Use the brief context: {brief.short_description}"
        )
        consistency_prompt = self._string(character.get("consistencyPrompt")) or (
            "Preserve the same actor identity, face, body type, outfit, age range, and commercial styling across all keyframes."
        )
        return {
            "name": self._string(character.get("name")) or "Primary actor",
            "description": description,
            "imagePrompt": image_prompt,
            "consistencyPrompt": consistency_prompt,
            "status": character.get("status") or "pending",
            "imageUrl": character.get("imageUrl"),
            "candidateImages": character.get("candidateImages") if isinstance(character.get("candidateImages"), list) else [],
        }

    def _coerce_product_references(self, value: list[Any], project: Project, vision: VisionAnalysis) -> list[dict[str, Any]]:
        uploaded_files = list(project.uploaded_files)
        file_by_id = {item.id: item for item in uploaded_files}
        file_order = {item.id: index + 1 for index, item in enumerate(uploaded_files)}
        references: list[dict[str, Any]] = []
        seen: set[str] = set()

        for raw_reference in value:
            if not isinstance(raw_reference, dict):
                continue
            reference_id = self._string(raw_reference.get("id"))
            if not reference_id:
                continue

            reference = dict(raw_reference)
            uploaded_file = file_by_id.get(reference_id)
            if uploaded_file:
                display_name = uploaded_file.file_name
                clean_display_name = self._clean_uploaded_file_label(uploaded_file.file_name)
                order = file_order.get(reference_id, len(references) + 1)
                reference["name"] = display_name
                reference["sourceFileName"] = uploaded_file.file_name
                reference["referenceLabel"] = self._product_reference_label(uploaded_file.file_name, order, clean_display_name)
                reference["visualDescription"] = self._string(reference.get("visualDescription")) or (
                    f"Uploaded product reference image named {uploaded_file.file_name}."
                )
                reference["lockPrompt"] = self._string(reference.get("lockPrompt")) or (
                    f"Preserve the visible product/app details from {uploaded_file.file_name}."
                )
                reference["useWhen"] = self._string(reference.get("useWhen")) or "Use when this uploaded reference is visible in the scene."
                reference["kind"] = self._string(reference.get("kind")) or "other"
                reference["isPrimary"] = bool(reference.get("isPrimary", True))
            references.append(reference)
            seen.add(reference_id)

        for uploaded_file in uploaded_files:
            if uploaded_file.id in seen:
                continue
            display_name = uploaded_file.file_name
            clean_display_name = self._clean_uploaded_file_label(uploaded_file.file_name)
            order = file_order.get(uploaded_file.id, len(references) + 1)
            references.append(
                {
                    "id": uploaded_file.id,
                    "name": display_name,
                    "sourceFileName": uploaded_file.file_name,
                    "referenceLabel": self._product_reference_label(uploaded_file.file_name, order, clean_display_name),
                    "kind": "uploaded_product_reference",
                    "visualDescription": f"Uploaded product reference image named {uploaded_file.file_name}.",
                    "lockPrompt": f"Preserve the visible product/app details from {uploaded_file.file_name}.",
                    "useWhen": "Use when this uploaded reference is visible in the scene.",
                    "isPrimary": True,
                }
            )

        if references:
            return references

        return [
            {
                "id": "vision_summary",
                "name": "Vision Summary",
                "referenceLabel": "product_ref_01_vision_summary",
                "kind": "vision_summary",
                "visualDescription": "; ".join(vision.detected_ui_elements + vision.detected_objects) or "No uploaded product image.",
                "lockPrompt": "Use only product details supported by the brief and vision analysis.",
                "useWhen": "Use for text-only planning when no product reference image was uploaded.",
                "isPrimary": True,
            }
        ]

    def _coerce_primary_location(self, value: Any, project: Project, brief: NormalizedBrief) -> dict[str, Any]:
        location = value if isinstance(value, dict) else {}
        description = self._string(location.get("description")) or "Single consistent commercial setting for this ad."
        image_prompt = self._string(location.get("imagePrompt")) or (
            f"Realistic commercial location reference for an ad about {project.product_name}. "
            f"Use the brief context: {brief.short_description}"
        )
        consistency_prompt = self._string(location.get("consistencyPrompt")) or (
            "Preserve the same location, lighting, layout, surface, recurring props, and background anchors across all keyframes."
        )
        return {
            "name": self._string(location.get("name")) or "Primary setting",
            "description": description,
            "imagePrompt": image_prompt,
            "consistencyPrompt": consistency_prompt,
            "status": location.get("status") or "pending",
            "imageUrl": location.get("imageUrl"),
            "candidateImages": location.get("candidateImages") if isinstance(location.get("candidateImages"), list) else [],
        }

    def _target_scene_count(self, project: Project) -> int:
        text = "\n".join(
            part
            for part in [
                project.brief or "",
                project.product_description or "",
            ]
            if part
        )
        non_empty_lines = [
            line.strip()
            for line in text.splitlines()
            if line.strip() and not line.strip().endswith(":")
        ]
        sentence_count = len(re.findall(r"[.!?。！？]+", text))
        bullet_count = len(re.findall(r"(?m)^\s*[-*•]\s+", text))
        quoted_dialogue_count = len(re.findall(r'"[^"]+"|“[^”]+”|<[^>]+>', text))
        complexity = max(len(non_empty_lines), sentence_count, bullet_count, quoted_dialogue_count)
        if complexity >= 10 or len(text) > 1800:
            return 8
        if complexity >= 7 or len(text) > 1200:
            return 7
        if complexity >= 4 or len(text) > 500:
            return 6
        return 5

    def _coerce_scene_clips(self, scenes: list[Any], product_references: list[dict[str, Any]]) -> list[dict[str, Any]]:
        coerced_scenes: list[dict[str, Any]] = []
        previous_outcome = ""
        for index, raw_scene in enumerate(scenes):
            if not isinstance(raw_scene, dict):
                continue
            scene = dict(raw_scene)
            scene["sceneIndex"] = index + 1
            scene["durationSec"] = self._normalize_scene_duration(scene.get("durationSec"))
            scene["openingState"] = self._string(scene.get("openingState")) or (
                previous_outcome
                or "A stable neutral pose immediately before this scene's action begins; no action result is visible yet."
            )
            scene["voiceLines"] = self._coerce_voice_lines(scene.get("voiceLines"), scene["durationSec"])
            for text_key in ("visualAction", "productMoment", "characterAction", "locationUse"):
                if scene.get(text_key):
                    scene[text_key] = self._replace_reference_aliases(str(scene.get(text_key) or ""), product_references)
            final_prompt = str(scene.get("finalVideoPrompt") or "").strip()
            if final_prompt:
                scene["finalVideoPrompt"] = self._replace_reference_aliases(self._clean_video_prompt(final_prompt), product_references)
            scene["keyframePrompts"] = self._coerce_keyframe_slots(scene, product_references)
            coerced_scenes.append(scene)
            previous_outcome = self._string(scene.get("visualAction")) or self._string(scene.get("sceneGoal"))
        return coerced_scenes

    def _coerce_voice_lines(self, value: Any, duration_seconds: int) -> list[dict[str, Any]]:
        lines = [dict(item) for item in value or [] if isinstance(item, dict)] if isinstance(value, list) else []
        total_words = sum(len(re.findall(r"\b[\w'-]+\b", self._string(item.get("line")), flags=re.UNICODE)) for item in lines)
        speakers = {self._string(item.get("speaker")) for item in lines if self._string(item.get("speaker"))}
        native_budget = max(1, int(duration_seconds * NATIVE_DIALOGUE_WORDS_PER_SECOND))
        force_post = len(lines) > 1 or len(speakers) > 1 or total_words > native_budget
        for item in lines:
            item["timing"] = f"0-{duration_seconds}s"
            requested_mode = self._string(item.get("generationMode")).lower()
            item["generationMode"] = "post_voiceover" if requested_mode == "post_voiceover" or force_post else "native"
        return lines

    def _coerce_keyframe_slots(self, scene: dict[str, Any], product_references: list[dict[str, Any]]) -> list[dict[str, Any]]:
        raw_slots = scene.get("keyframePrompts") if isinstance(scene.get("keyframePrompts"), list) else []
        slots = [slot for slot in raw_slots if isinstance(slot, dict)][:KEYFRAMES_PER_SCENE]
        while len(slots) < KEYFRAMES_PER_SCENE:
            slot_id = "kf_main"
            label = "Opening keyframe"
            timing = "0s"
            purpose = "Frame 0 immediately before the scene action begins; no completed action or endpoint is visible."
            prompt = " ".join(
                str(value or "")
                for value in [
                    scene.get("title"),
                    scene.get("openingState"),
                    scene.get("locationUse"),
                    scene.get("camera", {}).get("composition") if isinstance(scene.get("camera"), dict) else "",
                    purpose,
                ]
            ).strip()
            slots.append(
                {
                    "id": slot_id,
                    "label": label,
                    "timing": timing,
                    "purpose": purpose,
                    "prompt": prompt,
                    "productReferenceIds": [],
                }
            )

        normalized_slots: list[dict[str, Any]] = []
        for index, slot in enumerate(slots):
            normalized_slot = dict(slot)
            normalized_slot["id"] = "kf_main"
            normalized_slot["label"] = self._string(normalized_slot.get("label")) or "Opening keyframe"
            normalized_slot["timing"] = "0s"
            normalized_slot["purpose"] = self._string(normalized_slot.get("purpose")) or "Frame 0 immediately before the scene action begins; no completed action or endpoint is visible."
            normalized_slot["prompt"] = self._replace_reference_aliases(str(normalized_slot.get("prompt") or ""), product_references)
            normalized_slot["productReferenceIds"] = self._normalize_slot_product_reference_ids(scene, normalized_slot, product_references)
            normalized_slots.append(normalized_slot)
        return normalized_slots

    def _normalize_scene_duration(self, value: Any) -> int:
        if isinstance(value, (int, float)):
            raw_duration = int(value)
        else:
            match = re.search(r"\d+", str(value or ""))
            raw_duration = int(match.group(0)) if match else DEFAULT_SCENE_CLIP_SECONDS
        return min(ALLOWED_SCENE_CLIP_SECONDS, key=lambda item: abs(item - raw_duration))

    def _normalize_slot_product_reference_ids(self, scene: dict[str, Any], slot: dict[str, Any], product_references: list[dict[str, Any]]) -> list[str]:
        aliases = self._reference_alias_lookup(product_references)
        reference_by_id = {str(reference.get("id") or ""): reference for reference in product_references}
        normalized: list[str] = []

        def add(reference_id: str) -> None:
            if reference_id and reference_id not in normalized:
                normalized.append(reference_id)

        searchable_text = " ".join(
            str(value or "")
            for value in [
                slot.get("prompt"),
                slot.get("purpose"),
                slot.get("label"),
                scene.get("title"),
                scene.get("visualAction"),
                scene.get("productMoment"),
            ]
        )
        lowered_text = searchable_text.lower()
        if self._blocks_uploaded_product_reference(lowered_text):
            return []
        if not self._needs_uploaded_product_reference(lowered_text):
            return []

        raw_ids = slot.get("productReferenceIds")
        if isinstance(raw_ids, list):
            for raw_id in raw_ids:
                key = str(raw_id or "").strip().lstrip("@")
                reference_id = aliases.get(key.lower(), key if key in aliases.values() else "")
                reference = reference_by_id.get(reference_id)
                if reference and self._reference_matches_slot_text(reference, lowered_text):
                    add(reference_id)

        for alias, reference_id in aliases.items():
            if alias and alias in lowered_text:
                add(reference_id)

        if not normalized:
            for reference in self._keyword_matched_references(lowered_text, product_references):
                add(str(reference.get("id") or ""))

        return self._prioritize_product_reference_ids(normalized, lowered_text, reference_by_id)[:1]

    def _blocks_uploaded_product_reference(self, lowered_text: str) -> bool:
        blocking_phrases = (
            "no app visible",
            "no app is visible",
            "no app visible yet",
            "no app visible.",
            "no app/product visible",
            "no product visible",
            "no product reference visible",
            "no uploaded product reference visible",
            "no ui visible",
            "no screen visible",
            "phone is lowered slightly, out of focus",
            "phone is now slightly out of focus",
            "not showing the app yet",
            "phone is visible but kept hidden",
            "out of focus below frame",
            "focus on character and cta",
            "focus on the physical coin",
        )
        return any(phrase in lowered_text for phrase in blocking_phrases)

    def _needs_uploaded_product_reference(self, lowered_text: str) -> bool:
        return self._contains_any_keyword(
            lowered_text,
            (
                "phone screen",
                "smartphone screen",
                "app screen",
                "mobile app screen",
                "ui",
                "interface",
                "scan",
                "scanning",
                "capture button",
                "identify",
                "result",
                "detail",
                "reference price",
                "price range",
                "value range",
                "logo",
                "packaging",
                "package",
                "bottle",
                "jar",
                "tube",
                "box",
                "label",
            ),
        )

    def _reference_matches_slot_text(self, reference: dict[str, Any], lowered_text: str) -> bool:
        reference_text = " ".join(
            str(reference.get(key) or "")
            for key in ("name", "sourceFileName", "referenceLabel", "visualDescription", "useWhen", "kind")
        ).lower()

        direct_aliases = [
            str(reference.get("id") or "").lower(),
            str(reference.get("name") or "").lower(),
            str(reference.get("sourceFileName") or "").lower(),
            str(reference.get("referenceLabel") or "").lower(),
            Path(str(reference.get("sourceFileName") or "")).stem.lower(),
        ]
        if any(alias and alias in lowered_text for alias in direct_aliases):
            return True

        is_app_reference = self._contains_any_keyword(reference_text, ("app", "screen", "ui", "scan", "result", "detail", "home", "interface"))
        if is_app_reference:
            groups = [
                (("detail", "result", "value", "price", "rarity", "reference price", "price range"), ("detail", "result", "value", "price", "rarity", "coin_detail")),
                (("scan", "scanning", "capture button", "identify", "camera interface", "scan interface"), ("scan", "camera", "capture", "scan interface")),
                (("home screen", "start screen", "app home", "main screen"), ("home", "start")),
            ]
            return any(
                self._contains_any_keyword(lowered_text, scene_keywords)
                and self._contains_any_keyword(reference_text, reference_keywords)
                for scene_keywords, reference_keywords in groups
            )

        return self._contains_any_keyword(lowered_text, ("visible product reference", "uploaded product", "logo", "packaging", "package", "bottle", "jar", "tube", "box", "label"))

    def _contains_any_keyword(self, lowered_text: str, keywords: tuple[str, ...]) -> bool:
        for keyword in keywords:
            normalized_keyword = keyword.lower()
            if " " in normalized_keyword or "_" in normalized_keyword:
                if normalized_keyword in lowered_text:
                    return True
                continue
            if re.search(rf"(?<![a-z0-9]){re.escape(normalized_keyword)}(?![a-z0-9])", lowered_text):
                return True
        return False

    def _reference_alias_lookup(self, product_references: list[dict[str, Any]]) -> dict[str, str]:
        aliases: dict[str, str] = {}
        for reference in product_references:
            reference_id = str(reference.get("id") or "").strip()
            if not reference_id:
                continue
            for value in [
                reference.get("id"),
                reference.get("name"),
                reference.get("sourceFileName"),
                reference.get("referenceLabel"),
                Path(str(reference.get("sourceFileName") or "")).stem,
            ]:
                text = str(value or "").strip().lstrip("@")
                if text:
                    aliases[text.lower()] = reference_id
        return aliases

    def _keyword_matched_references(self, lowered_text: str, product_references: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not lowered_text or not product_references:
            return []
        if not self._needs_uploaded_product_reference(lowered_text):
            return []

        groups = [
            (("detail", "result", "value", "price", "rarity", "save", "cta"), ("detail", "result", "value", "price", "rarity", "coin_detail")),
            (("scan", "scanning", "capture button", "identify", "camera interface", "scan interface"), ("scan", "camera", "capture", "scan interface")),
            (("home screen", "start screen", "app home", "main screen"), ("home", "start")),
        ]
        matched: list[dict[str, Any]] = []
        for scene_keywords, reference_keywords in groups:
            if not self._contains_any_keyword(lowered_text, scene_keywords):
                continue
            for reference in product_references:
                reference_text = " ".join(
                    str(reference.get(key) or "")
                    for key in ("name", "sourceFileName", "referenceLabel", "visualDescription", "useWhen", "kind")
                ).lower()
                if self._contains_any_keyword(reference_text, reference_keywords) and reference not in matched:
                    matched.append(reference)
        return matched

    def _prioritize_product_reference_ids(
        self,
        reference_ids: list[str],
        lowered_text: str,
        reference_by_id: dict[str, dict[str, Any]],
    ) -> list[str]:
        if len(reference_ids) <= 1:
            return reference_ids

        priority_groups = [
            (("detail", "result", "value", "price", "rarity", "reference price", "price range"), ("detail", "result", "value", "price", "rarity", "coin_detail")),
            (("scan", "scanning", "capture button", "identify", "camera interface", "scan interface"), ("scan", "camera", "capture", "scan interface")),
            (("home screen", "start screen", "app home", "main screen"), ("home", "start")),
        ]
        for scene_keywords, reference_keywords in priority_groups:
            if not self._contains_any_keyword(lowered_text, scene_keywords):
                continue
            ranked = [
                reference_id
                for reference_id in reference_ids
                if self._contains_any_keyword(self._reference_search_text(reference_by_id.get(reference_id, {})), reference_keywords)
            ]
            if ranked:
                return ranked
        return [reference_ids[0]]

    def _reference_search_text(self, reference: dict[str, Any]) -> str:
        return " ".join(
            str(reference.get(key) or "")
            for key in ("name", "sourceFileName", "referenceLabel", "visualDescription", "useWhen", "kind")
        ).lower()

    def _replace_reference_aliases(self, value: str, product_references: list[dict[str, Any]]) -> str:
        next_value = value
        replacements: list[tuple[str, str]] = []
        for reference in product_references:
            mention = self._reference_mention(reference)
            if not mention:
                continue
            mention_target = mention.lstrip("@").lower()
            for raw_alias in [reference.get("id"), reference.get("referenceLabel"), Path(str(reference.get("sourceFileName") or "")).stem]:
                alias = str(raw_alias or "").strip()
                if alias and alias.lower() in mention_target:
                    continue
                if alias and alias != mention.lstrip("@"):
                    replacements.append((alias, mention))
        for alias, mention in sorted(replacements, key=lambda item: len(item[0]), reverse=True):
            next_value = next_value.replace(alias, mention)
        next_value = re.sub(r"@+", "@", next_value)
        next_value = re.sub(r"(@[A-Za-z0-9_.-]+?\.(?:jpe?g|png|webp|gif))(?:\.(?:jpe?g|png|webp|gif))+", r"\1", next_value, flags=re.IGNORECASE)
        return next_value

    def _reference_mention(self, reference: dict[str, Any]) -> str:
        source_file_name = str(reference.get("sourceFileName") or "").strip()
        if source_file_name:
            return f"@{source_file_name}"
        reference_label = str(reference.get("referenceLabel") or "").strip()
        if reference_label:
            return f"@{reference_label}"
        reference_id = str(reference.get("id") or "").strip()
        return f"@{reference_id}" if reference_id else ""

    def _clean_video_prompt(self, prompt: str) -> str:
        cleaned = prompt.strip()
        cleaned = re.sub(
            r"^\s*Create\s+(?:exactly\s+)?(?:one\s+)?(?:an?\s+)?\d+\s*[- ]seconds?\s+(?:vertical\s+)?(?:\d+:\d+\s+)?(?:ad\s+)?(?:video|clip)\.?\s*",
            "",
            cleaned,
            flags=re.IGNORECASE,
        )
        cleaned = re.sub(r"\bCreate an? \d+\s*[- ]seconds? vertical video\.\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\bexact(?:ly)? \d+\s*[- ]seconds? duration,?\s*", "", cleaned, flags=re.IGNORECASE)
        return cleaned.strip() or prompt.strip()

    def _product_references_payload(self, project: Project, vision: VisionAnalysis) -> list[dict[str, Any]]:
        if project.uploaded_files:
            return [
                {
                    "id": item.id,
                    "file_name": item.file_name,
                    "suggested_reference_label": self._product_reference_label(
                        item.file_name,
                        index + 1,
                        self._clean_uploaded_file_label(item.file_name),
                    ),
                    "suggested_display_name": self._clean_uploaded_file_label(item.file_name),
                    "content_type": item.content_type,
                    "url": item.url,
                    "kind_hint": "uploaded_product_reference",
                }
                for index, item in enumerate(project.uploaded_files)
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

    def _clean_uploaded_file_label(self, file_name: str) -> str:
        stem = Path(file_name).stem
        stem = re.sub(r"^product_ref_\d+_", "", stem, flags=re.IGNORECASE)
        stem = re.sub(r"_[0-9]{8,14}$", "", stem)
        stem = Path(stem).stem
        stem = re.sub(r"[^a-zA-Z0-9]+", " ", stem).strip()
        if not stem:
            return "Product Reference"
        return " ".join(part.capitalize() for part in stem.split())

    def _product_reference_label(self, file_name: str, order: int, display_name: str) -> str:
        stem = Path(file_name).stem
        if re.match(r"^product_ref_\d+_", stem, flags=re.IGNORECASE):
            return self._slug(stem)
        return f"product_ref_{order:02d}_{self._slug(display_name)}"

    def _slug(self, value: str) -> str:
        slug = re.sub(r"[^a-zA-Z0-9]+", "_", value.lower()).strip("_")
        return slug or "reference"

    def _string_list(self, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return [self._string(item) for item in value if self._string(item)]
        return [item.strip() for item in str(value).replace("\n", ",").replace(";", ",").split(",") if item.strip()]
