from typing import Protocol

from app.models.schemas import CreativeAngle, ProductBrief, ProductIntelligenceBrief, Project, StoryboardScene, Variant


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


class RuleBasedVariantScriptGenerator:
    def generate(
        self,
        project: Project,
        brief: ProductBrief,
        angles: list[CreativeAngle],
        intelligence: ProductIntelligenceBrief | None = None,
    ) -> list[Variant]:
        intelligence = intelligence or self._fallback_intelligence(project, brief)
        return [
            self._build_variant(project, brief, intelligence, angle, index)
            for index, angle in enumerate(angles, start=1)
        ]

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

    def _fallback_intelligence(self, project: Project, brief: ProductBrief) -> ProductIntelligenceBrief:
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
