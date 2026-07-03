import json
from typing import Any, Protocol

from app.models.schemas import (
    CreativeAngle,
    ProductBrief,
    ProductIntelligenceBrief,
    Project,
    StoryboardScene,
    Variant,
)
from app.services.character_planner import GeminiCharacterPlanner
from app.services.character_reference_generator import GeminiCharacterReferenceGenerator
from app.services.intelligence_context import compact_intelligence_context, compact_project_context
from app.services.llm_provider import LLMProvider, build_llm_provider
from app.services.production_prompt_generator import GeminiProductionPromptGenerator


BASE_NEGATIVE_PROMPT = (
    "different product, wrong brand, unreadable text, distorted hands, extra fingers, deformed face, "
    "blurry product, low quality, random logo, fake UI text, exaggerated claims"
)


class VariantScriptGenerator(Protocol):
    def generate(
        self,
        project: Project,
        brief: ProductBrief,
        angles: list[CreativeAngle],
        intelligence: ProductIntelligenceBrief | None = None,
    ) -> list[Variant]:
        ...


class GeminiVariantScriptGenerator:
    RESPONSE_SCHEMA = {
        "type": "object",
        "properties": {
            "variant": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "duration": {"type": "string"},
                    "format": {"type": "string"},
                    "hook": {"type": "string"},
                    "script": {"type": "string"},
                    "storyboard": {
                        "type": "array",
                        "minItems": 4,
                        "maxItems": 4,
                        "items": {
                            "type": "object",
                            "properties": {
                                "scene_number": {"type": "integer"},
                                "duration_seconds": {"type": "integer"},
                                "objective": {"type": "string"},
                                "visual_description": {"type": "string"},
                                "camera_angle": {"type": "string"},
                                "on_screen_text": {"type": "string"},
                                "voiceover_line": {"type": "string"},
                                "transition": {"type": "string"},
                                "generation_prompt": {"type": "string"},
                                "negative_prompt": {"type": "string"},
                            },
                            "required": [
                                "scene_number",
                                "duration_seconds",
                                "objective",
                                "visual_description",
                                "camera_angle",
                                "on_screen_text",
                                "voiceover_line",
                                "transition",
                                "generation_prompt",
                                "negative_prompt",
                            ],
                        },
                    },
                    "voiceover": {"type": "string"},
                },
                "required": [
                    "name",
                    "duration",
                    "format",
                    "hook",
                    "script",
                    "storyboard",
                    "voiceover",
                ],
            }
        },
        "required": ["variant"],
    }

    def __init__(self, llm_provider: LLMProvider | None = None) -> None:
        self.llm_provider = llm_provider or build_llm_provider()
        self.character_planner = GeminiCharacterPlanner(self.llm_provider)
        self.character_reference_generator = GeminiCharacterReferenceGenerator(self.llm_provider)
        self.production_prompt_generator = GeminiProductionPromptGenerator(self.llm_provider)

    def generate(
        self,
        project: Project,
        brief: ProductBrief,
        angles: list[CreativeAngle],
        intelligence: ProductIntelligenceBrief | None = None,
    ) -> list[Variant]:
        intelligence = intelligence or self._compat_intelligence(project, brief)
        return [
            self._build_variant_with_llm(project, intelligence, angle, index)
            for index, angle in enumerate(angles, start=1)
        ]

    def _build_variant_with_llm(
        self,
        project: Project,
        intelligence: ProductIntelligenceBrief,
        angle: CreativeAngle,
        index: int,
    ) -> Variant:
        playbook = intelligence.recommended_ad_playbooks[0].model_dump(mode="json") if intelligence.recommended_ad_playbooks else None
        prompt = (
            "You are the Script + Storyboard Agent for a short-form video ad factory. "
            "Create one publish-ready UGC video ad variant from the selected creative angle. "
            "Return JSON only in this exact shape: {\"variant\": {...}}. "
            "The variant object must include these exact keys: name, duration, format, hook, script, "
            "storyboard, voiceover. "
            "Create exactly 4 storyboard scenes. "
            "Scene 1: hook. Scene 2: problem/setup. Scene 3: product demo/proof. Scene 4: result + CTA. "
            "Every scene must include scene_number, duration_seconds, objective, visual_description, camera_angle, "
            "on_screen_text, voiceover_line, transition, generation_prompt, negative_prompt. "
            "Negative prompts must include: different product, wrong brand, unreadable text, distorted hands, "
            "extra fingers, deformed face, blurry product, low quality, random logo, fake UI text. "
            "For app products, generation_prompt must say: phone screen should be clean and simple for later UI overlay, "
            "do not generate unreadable app text. Avoid unsafe or exaggerated claims.\n\n"
            f"Project:\n{json.dumps(compact_project_context(project), ensure_ascii=False, indent=2)}\n\n"
            f"Product intelligence:\n{json.dumps(compact_intelligence_context(intelligence), ensure_ascii=False, indent=2)}\n\n"
            f"Selected creative angle:\n{json.dumps(angle.model_dump(mode='json'), ensure_ascii=False, indent=2)}\n\n"
            f"Selected playbook:\n{json.dumps(playbook, ensure_ascii=False, indent=2)}\n\n"
            f"Variant index: {index}"
        )
        data = self.llm_provider.generate_json(prompt, temperature=0.55, response_schema=self.RESPONSE_SCHEMA)
        raw_variant = data.get("variant")
        if not isinstance(raw_variant, dict):
            raise ValueError("Gemini script response must include a variant object")
        raw_variant = self._coerce_variant(raw_variant, project, intelligence, angle, index, playbook)
        variant = Variant.model_validate(raw_variant)
        if len(variant.storyboard) != 4:
            raise ValueError("Gemini variant must include exactly 4 storyboard scenes")
        if not variant.scene_prompts:
            variant.scene_prompts = [scene.generation_prompt for scene in variant.storyboard]
        if not variant.subtitles:
            variant.subtitles = [scene.voiceover_line for scene in variant.storyboard]
        if not variant.voiceover:
            variant.voiceover = " ".join(variant.subtitles)
        character_plan, character_bible = self.character_planner.plan(
            product_intelligence=intelligence,
            creative_angle=angle,
            variant=variant,
            platform=project.platform,
            tone=project.tone,
        )
        character_reference_prompts = self.character_reference_generator.generate(
            character_bible=character_bible,
            product_intelligence=intelligence,
            creative_angle=angle,
            variant=variant,
        )
        variant.production_package = self.production_prompt_generator.generate(
            project=project,
            product_intelligence=intelligence,
            creative_angle=angle,
            variant=variant,
            character_plan=character_plan,
            character_bible=character_bible,
            character_reference_prompts=character_reference_prompts,
        )
        return variant

    def _coerce_variant(
        self,
        raw_variant: dict[str, Any],
        project: Project,
        intelligence: ProductIntelligenceBrief,
        angle: CreativeAngle,
        index: int,
        playbook: dict[str, Any] | None,
    ) -> dict[str, Any]:
        storyboard = raw_variant.get("storyboard") or raw_variant.get("scenes") or raw_variant.get("storyboard_scenes")
        if not isinstance(storyboard, list):
            storyboard = []
        scenes = [
            self._coerce_scene(scene, scene_index, project, intelligence, angle)
            for scene_index, scene in enumerate(storyboard[:4], start=1)
        ]
        if len(scenes) != 4:
            raise ValueError("Gemini variant must include exactly 4 storyboard scenes")

        subtitles = raw_variant.get("subtitles")
        if not isinstance(subtitles, list) or not subtitles:
            subtitles = [scene["voiceover_line"] for scene in scenes]

        voiceover = self._string_from(raw_variant, "voiceover", "voice_over", "vo")
        if not voiceover:
            voiceover = " ".join(subtitles)

        script = self._string_from(raw_variant, "script", "full_script", "video_script")
        if not script:
            script = "\n".join(
                f"Scene {scene['scene_number']} ({scene['duration_seconds']}s): {scene['voiceover_line']}"
                for scene in scenes
            )

        return {
            "angle_id": angle.id,
            "name": self._string_from(raw_variant, "name", "variant_name", "title") or f"Variant {index}: {angle.name}",
            "duration": self._string_from(raw_variant, "duration") or project.duration,
            "format": self._string_from(raw_variant, "format", "aspect_ratio") or "9:16",
            "hook": self._string_from(raw_variant, "hook", "opening_hook") or angle.hook,
            "script": script,
            "storyboard": scenes,
            "scene_prompts": [scene["generation_prompt"] for scene in scenes],
            "voiceover": voiceover,
            "subtitles": [str(item).strip() for item in subtitles if str(item).strip()],
            "title": self._string_from(raw_variant, "title", "ad_title") or f"{project.product_name}: {angle.name}",
            "caption": self._string_from(raw_variant, "caption", "social_caption", "post_caption")
            or f"{angle.hook} {angle.cta}.",
            "cover_prompt": self._string_from(raw_variant, "cover_prompt", "thumbnail_prompt", "cover_image_prompt")
            or f"UGC cover frame for {project.product_name}, creator holding phone and old coin, bold readable hook text.",
            "selected_playbook": playbook["name"] if playbook else None,
            "angle_type": angle.angle_type,
        }

    def _coerce_scene(
        self,
        raw_scene: Any,
        index: int,
        project: Project,
        intelligence: ProductIntelligenceBrief,
        angle: CreativeAngle,
    ) -> dict[str, Any]:
        if not isinstance(raw_scene, dict):
            raise ValueError(f"Gemini storyboard scene {index} must be an object")

        objective = self._string_from(raw_scene, "objective", "goal", "scene_objective") or self._default_scene_objective(index)
        visual = self._string_from(raw_scene, "visual_description", "visual", "shot_description") or angle.proof_demo_moment
        camera = self._string_from(raw_scene, "camera_angle", "camera", "shot") or "Handheld UGC vertical shot."
        on_screen_text = self._string_from(raw_scene, "on_screen_text", "text_overlay", "overlay_text") or (
            angle.hook if index == 1 else angle.cta if index == 4 else objective
        )
        voiceover_line = self._string_from(raw_scene, "voiceover_line", "voiceover", "vo_line") or on_screen_text
        generation_prompt = self._string_from(raw_scene, "generation_prompt", "prompt", "video_prompt")
        if not generation_prompt:
            generation_prompt = (
                f"Vertical UGC ad scene for {project.product_name}. {visual} Camera: {camera}. "
                f"Style: {intelligence.brand_style_notes}"
            )

        return {
            "scene_number": self._int_from(raw_scene.get("scene_number") or raw_scene.get("scene"), index),
            "duration_seconds": self._int_from(raw_scene.get("duration_seconds") or raw_scene.get("duration"), 5),
            "objective": objective,
            "visual_description": visual,
            "camera_angle": camera,
            "on_screen_text": on_screen_text,
            "voiceover_line": voiceover_line,
            "transition": self._string_from(raw_scene, "transition") or "Cut.",
            "generation_prompt": generation_prompt,
            "negative_prompt": self._string_from(raw_scene, "negative_prompt") or BASE_NEGATIVE_PROMPT,
        }

    def _string_from(self, item: dict[str, Any], *keys: str) -> str:
        for key in keys:
            value = item.get(key)
            if value is None:
                continue
            if isinstance(value, list):
                value = " ".join(str(part).strip() for part in value if str(part).strip())
            value = str(value).strip()
            if value:
                return value
        return ""

    def _int_from(self, value: Any, default_value: int) -> int:
        try:
            parsed = int(float(str(value).replace("s", "").strip()))
        except (TypeError, ValueError):
            parsed = default_value
        return max(1, parsed)

    def _default_scene_objective(self, index: int) -> str:
        objectives = {
            1: "Hook the viewer.",
            2: "Set up the problem.",
            3: "Show the product demo.",
            4: "Show result and CTA.",
        }
        return objectives.get(index, "Move the story forward.")

    def _build_variant(
        self,
        project: Project,
        brief: ProductBrief,
        intelligence: ProductIntelligenceBrief,
        angle: CreativeAngle,
        index: int,
    ) -> Variant:
        duration = project.duration or "20s"
        cta = intelligence.recommended_cta or project.cta or angle.cta
        product = project.product_name
        playbook = intelligence.recommended_ad_playbooks[0] if intelligence.recommended_ad_playbooks else None
        scenes = self._scenes_for_type(project, intelligence, angle, cta)
        voiceover = " ".join(scene.voiceover_line for scene in scenes)
        subtitles = [scene.voiceover_line for scene in scenes]
        script = "\n".join(
            f"Scene {scene.scene_number} ({scene.duration_seconds}s): {scene.voiceover_line}"
            for scene in scenes
        )

        return Variant(
            angle_id=angle.id,
            name=f"Variant {index}: {angle.name}",
            duration=duration,
            format="9:16",
            hook=angle.hook,
            script=script,
            storyboard=scenes,
            scene_prompts=[scene.generation_prompt for scene in scenes],
            voiceover=voiceover,
            subtitles=subtitles,
            title=f"{product}: {angle.name}",
            caption=f"{angle.hook} {cta}. #{self._slug(project.platform)} #ugc #productdemo",
            cover_prompt=(
                f"Cover frame for {product}: creator holding or pointing to the key product moment, "
                f"bold readable hook text, clean brand-safe layout."
            ),
            selected_playbook=playbook.name if playbook else None,
            angle_type=angle.angle_type,
        )

    def _scenes_for_type(
        self,
        project: Project,
        intelligence: ProductIntelligenceBrief,
        angle: CreativeAngle,
        cta: str,
    ) -> list[StoryboardScene]:
        if intelligence.product_type == "skincare":
            return self._skincare_scenes(project, intelligence, angle, cta)
        if intelligence.product_type == "fnb":
            return self._fnb_scenes(project, intelligence, angle, cta)
        if intelligence.product_type == "education":
            return self._education_scenes(project, intelligence, angle, cta)
        if intelligence.product_type == "ecommerce":
            return self._ecommerce_scenes(project, intelligence, angle, cta)
        if intelligence.product_type == "mobile_app":
            return self._mobile_app_scenes(project, intelligence, angle, cta)
        return self._general_scenes(project, intelligence, angle, cta)

    def _mobile_app_scenes(
        self,
        project: Project,
        intelligence: ProductIntelligenceBrief,
        angle: CreativeAngle,
        cta: str,
    ) -> list[StoryboardScene]:
        product = project.product_name
        demo = self._demo(intelligence, 2)
        result = self._benefit(intelligence, 0)
        return [
            self._scene(
                1,
                4,
                "Hook with the object or user problem.",
                f"Creator holds the relevant object or shows the frustrating moment before using {product}.",
                "Handheld medium close-up, quick push-in.",
                angle.hook,
                angle.hook,
                "Fast cut.",
                f"Vertical phone-in-hand UGC. Show the real problem clearly before the app appears. {intelligence.brand_style_notes}",
                app_screen=True,
            ),
            self._scene(
                2,
                5,
                "Open the app and set up the action.",
                f"Creator opens {product} on a phone and points to the first simple action.",
                "Over-the-shoulder phone shot.",
                "Open the app",
                f"I opened {product} instead of guessing what to do next.",
                "Swipe into demo.",
                f"Show a clean phone screen for later UI overlay, simple app home screen, creator thumb starts {demo}.",
                app_screen=True,
            ),
            self._scene(
                3,
                7,
                "Use the key feature and show proof.",
                f"Show {angle.proof_demo_moment}.",
                "Close-up insert of phone and product/object.",
                result,
                self._safe_app_demo_line(project, intelligence),
                "Match cut to result.",
                f"Specific app demo for {product}: {demo}. Phone screen should be clean and simple for later UI overlay, do not generate unreadable app text.",
                app_screen=True,
            ),
            self._scene(
                4,
                5,
                "Show result and CTA.",
                f"Creator reacts to the result and gestures to download or try {product}.",
                "Front-facing close-up with phone visible.",
                cta,
                f"So now I know the next step. {cta}.",
                "End card.",
                f"UGC end card, phone visible, clean space for logo and CTA overlay, {project.platform} vertical ad.",
                app_screen=True,
            ),
        ]

    def _skincare_scenes(self, project: Project, intelligence: ProductIntelligenceBrief, angle: CreativeAngle, cta: str) -> list[StoryboardScene]:
        product = project.product_name
        return [
            self._scene(1, 4, "Hook around skin concern.", f"Creator shows a realistic routine moment and mentions {angle.pain_point}.", "Mirror close-up, natural bathroom light.", angle.hook, angle.hook, "Cut on gesture.", f"Realistic skincare UGC, no extreme before-after, natural skin texture visible, {intelligence.brand_style_notes}"),
            self._scene(2, 5, "Show product texture or application.", f"Close-up of {product} texture on fingertips or hand.", "Macro product shot.", "Texture check", f"I add {product} as one simple step, not a whole complicated routine.", "Soft cut.", f"Skincare texture macro, product bottle visible, gentle application, clean bathroom counter."),
            self._scene(3, 7, "Show routine fit and proof moment.", f"Apply {product} in a normal evening or morning routine.", "Medium close-up, mirror angle.", self._benefit(intelligence, 0), f"It fits right after cleansing and helps my skin look smoother over time.", "Match cut.", f"Routine demo with realistic application amount, calm pacing, product remains clearly visible."),
            self._scene(4, 5, "Set realistic expectation and CTA.", f"Creator places {product} near sink and points to CTA.", "Front-facing close-up.", cta, f"If you want a simple routine step for rough-looking texture, {cta.lower()}.", "Clean end card.", f"Skincare UGC end card, realistic expectation, no medical claims, brand-safe CTA."),
        ]

    def _fnb_scenes(self, project: Project, intelligence: ProductIntelligenceBrief, angle: CreativeAngle, cta: str) -> list[StoryboardScene]:
        product = project.product_name
        return [
            self._scene(1, 4, "Create craving or low-energy hook.", f"Creator at desk or outside during afternoon slump, craving {product}.", "Handheld face-to-product cut.", angle.hook, angle.hook, "Quick cut.", f"Bright F&B UGC, afternoon setting, appetizing colors, {intelligence.brand_style_notes}"),
            self._scene(2, 5, "Show product close-up.", f"Close-up of {product}, ice, cup, pour, cream, or packaging detail.", "Macro close-up with slow push.", "Look at this", f"The first thing that got me was the creamy close-up.", "Cut to taste.", f"Appetizing drink or food close-up, visible texture, condensation, natural light."),
            self._scene(3, 7, "Show reaction or taste moment.", f"Creator takes a sip or bite and reacts naturally.", "Medium close-up, handheld.", self._benefit(intelligence, 0), f"It is exactly the kind of quick treat I want when the day feels long.", "Whip pan.", f"Natural taste reaction, no health claims, product remains in frame, delivery/order context if relevant."),
            self._scene(4, 5, "Offer and CTA.", f"Show order screen, counter pickup, or product in hand with CTA.", "Product and phone close-up.", cta, f"If you need a quick break, {cta.lower()}.", "End card.", f"F&B end card with product close-up, CTA overlay, no medical or health claims."),
        ]

    def _education_scenes(self, project: Project, intelligence: ProductIntelligenceBrief, angle: CreativeAngle, cta: str) -> list[StoryboardScene]:
        product = project.product_name
        return [
            self._scene(1, 4, "Show learning pain.", f"Creator struggles with a realistic beginner learning moment for {product}.", "Front-facing desk setup.", angle.hook, angle.hook, "Cut to screen.", f"Education app UGC, learner at desk, relatable frustration, {intelligence.brand_style_notes}", app_screen=True),
            self._scene(2, 5, "Show product method.", f"Open {product} and show a simple practice prompt.", "Over-the-shoulder phone shot.", "Practice one prompt", f"I used {product} for one tiny practice session instead of trying to study everything.", "Swipe to lesson.", f"Clean app screen for later UI overlay, simple lesson card, no unreadable generated text.", app_screen=True),
            self._scene(3, 7, "Show small learning win.", f"Creator completes one phrase, prompt, quiz, or speaking practice step.", "Phone insert plus creator reaction.", self._benefit(intelligence, 0), f"That small win made it easier to keep practicing.", "Match cut.", f"Show a clear practice flow and positive learner reaction, clean UI overlay space.", app_screen=True),
            self._scene(4, 5, "Sign up or install CTA.", f"Creator returns to camera and points to app CTA.", "Front-facing close-up.", cta, f"If you want a simple way to practice, {cta.lower()}.", "End card.", f"Education app end card, phone visible, simple CTA, no guaranteed fluency claim.", app_screen=True),
        ]

    def _ecommerce_scenes(self, project: Project, intelligence: ProductIntelligenceBrief, angle: CreativeAngle, cta: str) -> list[StoryboardScene]:
        product = project.product_name
        return [
            self._scene(1, 4, "Hook with practical problem.", f"Creator shows the everyday friction before using {product}.", "Handheld medium close-up.", angle.hook, angle.hook, "Fast cut.", f"Ecommerce UGC, natural home setup, product not over-staged, {intelligence.brand_style_notes}"),
            self._scene(2, 5, "Show product use.", f"Unbox or pick up {product} and show the first useful feature.", "Tabletop close-up.", "First thing I noticed", f"Here is the feature I wanted to see before buying.", "Cut to use.", f"Clean unboxing or product feature close-up, hands visible, product centered."),
            self._scene(3, 7, "Show before/after or practical result.", f"Use {product} in the actual scenario and show the practical change.", "Over-the-shoulder detail shot.", self._benefit(intelligence, 0), f"This is the part that makes it useful for everyday use.", "Match cut.", f"Hands-on product demo, clear before and after context, no exaggerated claims."),
            self._scene(4, 5, "CTA.", f"Creator holds {product} and points to CTA.", "Front-facing close-up.", cta, f"If this solves the same problem for you, {cta.lower()}.", "End card.", f"Ecommerce end card, product and CTA visible, clean background."),
        ]

    def _general_scenes(self, project: Project, intelligence: ProductIntelligenceBrief, angle: CreativeAngle, cta: str) -> list[StoryboardScene]:
        product = project.product_name
        return [
            self._scene(1, 4, "Hook viewer.", f"Creator introduces a real situation where {product} matters.", "Handheld close-up.", angle.hook, angle.hook, "Fast cut.", f"Natural UGC hook for {product}, clear product or context visible."),
            self._scene(2, 5, "Set problem.", f"Show the specific problem: {angle.pain_point}.", "Over-the-shoulder detail shot.", "This was the issue", f"The problem was simple: {angle.pain_point}", "Cut to product.", f"Realistic setup of the problem, no staged studio look."),
            self._scene(3, 7, "Demo product.", f"Show {angle.proof_demo_moment}.", "Close-up demo shot.", self._benefit(intelligence, 0), f"Then {product} makes the next step easier.", "Match cut.", f"Clear product demo, product stays in frame, specific action visible."),
            self._scene(4, 5, "Result and CTA.", f"Creator shows result and CTA.", "Front-facing close-up.", cta, f"If this would help your routine, {cta.lower()}.", "End card.", f"Clean UGC end card with product and CTA."),
        ]

    def _scene(
        self,
        scene_number: int,
        duration_seconds: int,
        objective: str,
        visual_description: str,
        camera_angle: str,
        on_screen_text: str,
        voiceover_line: str,
        transition: str,
        generation_prompt: str,
        app_screen: bool = False,
    ) -> StoryboardScene:
        app_instruction = (
            " Phone screen should be clean and simple for later UI overlay, do not generate unreadable app text."
            if app_screen
            else ""
        )
        return StoryboardScene(
            scene_number=scene_number,
            duration_seconds=duration_seconds,
            objective=objective,
            visual_description=visual_description,
            camera_angle=camera_angle,
            on_screen_text=on_screen_text,
            voiceover_line=voiceover_line,
            transition=transition,
            generation_prompt=f"{generation_prompt}{app_instruction}",
            negative_prompt=BASE_NEGATIVE_PROMPT,
        )

    def _benefit(self, intelligence: ProductIntelligenceBrief, index: int) -> str:
        if not intelligence.functional_benefits:
            return intelligence.core_use_case
        return intelligence.functional_benefits[min(index, len(intelligence.functional_benefits) - 1)]

    def _demo(self, intelligence: ProductIntelligenceBrief, index: int) -> str:
        if not intelligence.demo_moments:
            return "show the product in use"
        return intelligence.demo_moments[min(index, len(intelligence.demo_moments) - 1)]

    def _safe_app_demo_line(self, project: Project, intelligence: ProductIntelligenceBrief) -> str:
        if "coin" in f"{project.product_name} {project.product_description or ''}".lower():
            return (
                f"{project.product_name} scans the coin, shows coin details, and gives an estimated reference value "
                "so I know what to research next."
            )
        return f"Then {project.product_name} shows a clear result: {self._benefit(intelligence, 0)}."

    def _compat_intelligence(self, project: Project, brief: ProductBrief) -> ProductIntelligenceBrief:
        return ProductIntelligenceBrief(
            detected_product=project.product_name,
            product_category=brief.category,
            product_type=brief.product_type,
            core_use_case=brief.short_description,
            target_audience_segments=brief.target_audience,
            primary_audience=", ".join(brief.target_audience) or "target audience",
            pain_points=[brief.main_problem],
            emotional_triggers=brief.emotional_triggers,
            functional_benefits=brief.functional_benefits,
            proof_points=brief.proof_elements,
            demo_moments=brief.proof_elements,
            visual_assets_detected=[],
            brand_style_notes=brief.recommended_visual_style,
            safe_claims=brief.safe_claims,
            claims_to_avoid=brief.claims_to_avoid,
            recommended_ad_playbooks=[],
            recommended_video_formats=brief.recommended_ad_formats,
            recommended_hooks=[],
            recommended_cta=project.cta or "Learn more",
            confidence_score=0.5,
        )

    def _slug(self, value: str | None) -> str:
        return (value or "social").lower().replace(" ", "")
