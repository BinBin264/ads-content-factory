from typing import Protocol

from app.models.schemas import CreativeAngle, ProductBrief, Project, StoryboardScene, Variant


class VariantScriptGenerator(Protocol):
    def generate(self, project: Project, brief: ProductBrief, angles: list[CreativeAngle]) -> list[Variant]:
        ...


class RuleBasedVariantScriptGenerator:
    def generate(self, project: Project, brief: ProductBrief, angles: list[CreativeAngle]) -> list[Variant]:
        return [self._build_variant(project, brief, angle, index) for index, angle in enumerate(angles, start=1)]

    def _build_variant(self, project: Project, brief: ProductBrief, angle: CreativeAngle, index: int) -> Variant:
        duration = project.duration or "20s"
        cta = project.cta or angle.cta
        style = brief.recommended_visual_style
        product = project.product_name
        brand_color_text = ", ".join(project.brand_colors)
        brand_colors = f" Brand colors: {brand_color_text}." if brand_color_text else ""

        scenes = [
            StoryboardScene(
                scene_number=1,
                duration_seconds=4,
                objective="Hook the viewer with a relatable opening.",
                visual_description=f"Creator holds or shows {product} in a natural vertical video setup.",
                camera_angle="Handheld medium close-up, quick push-in.",
                on_screen_text=angle.hook,
                voiceover_line=angle.hook,
                transition="Fast cut on the last word.",
                generation_prompt=f"Vertical UGC ad, {style} Show {product} immediately, natural expression, readable caption.{brand_colors}",
                negative_prompt="blurry, distorted hands, unreadable text, unrealistic claims, medical guarantee",
            ),
            StoryboardScene(
                scene_number=2,
                duration_seconds=5,
                objective="Show the problem or setup before the product solves it.",
                visual_description=f"Quick visual setup of the audience struggling with: {angle.pain_point}",
                camera_angle="Over-the-shoulder detail shot, natural handheld movement.",
                on_screen_text="This used to slow me down.",
                voiceover_line=f"The annoying part is simple: {angle.pain_point}",
                transition="Swipe transition into product demo.",
                generation_prompt=f"Realistic problem setup for {brief.target_audience}, vertical social ad, authentic environment, no staged studio look.",
                negative_prompt="fearmongering, exaggerated before-after, unsafe usage, offensive content",
            ),
            StoryboardScene(
                scene_number=3,
                duration_seconds=7,
                objective="Demonstrate the product proof moment clearly.",
                visual_description=f"Show {angle.proof_demo_moment}. Keep the product action easy to understand.",
                camera_angle="Close-up insert shots mixed with screen or product macro.",
                on_screen_text=brief.main_benefit,
                voiceover_line=f"Then {product} makes the next step obvious: {brief.main_benefit}",
                transition="Match cut from demo to result.",
                generation_prompt=f"Clear product demonstration of {product}, focus on {angle.proof_demo_moment}, crisp lighting, concise captions, {style}",
                negative_prompt="overpromising results, fake UI, messy background, low resolution",
            ),
            StoryboardScene(
                scene_number=4,
                duration_seconds=5,
                objective="Land the result and ask for action.",
                visual_description=f"Creator shows the result, smiles naturally, and points to a simple CTA for {product}.",
                camera_angle="Front-facing close-up with product or screen visible.",
                on_screen_text=cta,
                voiceover_line=f"If you want {brief.main_benefit.lower()}, {cta.lower()} today.",
                transition="End card with logo/product and CTA.",
                generation_prompt=f"UGC end card for {product}, positive realistic reaction, clear CTA text '{cta}', platform {project.platform}.{brand_colors}",
                negative_prompt="hard-sell spam, fake countdown, misleading discount, unreadable logo",
            ),
        ]

        voiceover = " ".join(scene.voiceover_line for scene in scenes)
        subtitles = [scene.voiceover_line for scene in scenes]
        script = "\n".join(
            f"Scene {scene.scene_number} ({scene.duration_seconds}s): {scene.voiceover_line}"
            for scene in scenes
        )
        title = f"{product}: {angle.name}"
        caption = f"{angle.hook} {cta}. #{self._slug(project.platform)} #ugc #productdemo"

        return Variant(
            angle_id=angle.id,
            name=f"Variant {index}: {angle.name}",
            duration=duration,
            format="9:16 vertical short video",
            hook=angle.hook,
            script=script,
            storyboard=scenes,
            scene_prompts=[scene.generation_prompt for scene in scenes],
            voiceover=voiceover,
            subtitles=subtitles,
            title=title,
            caption=caption,
            cover_prompt=f"High-converting cover frame for {product}: creator holding product, bold readable hook text, clean brand-safe layout.",
        )

    def _slug(self, value: str | None) -> str:
        return (value or "social").lower().replace(" ", "")
