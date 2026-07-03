import json
from pathlib import Path
from typing import Protocol

from app.config import OUTPUTS_DIR, ensure_app_dirs
from app.models.schemas import Project, Variant
from app.services.video_prompt_optimizer import RuleBasedVideoPromptOptimizer


class VideoProvider(Protocol):
    def render_mock(self, project: Project, variants: list[Variant]) -> list[Variant]:
        ...


class MockVideoProvider:
    def __init__(self, outputs_dir: Path = OUTPUTS_DIR) -> None:
        self.outputs_dir = outputs_dir
        self.prompt_optimizer = RuleBasedVideoPromptOptimizer()
        ensure_app_dirs()

    def render_mock(self, project: Project, variants: list[Variant]) -> list[Variant]:
        project_dir = self.outputs_dir / project.id
        project_dir.mkdir(parents=True, exist_ok=True)

        rendered: list[Variant] = []
        for variant in variants:
            variant_dir = project_dir / variant.id
            variant_dir.mkdir(parents=True, exist_ok=True)
            variant.video_status = "ready"
            variant.mock_video_url = f"/outputs/{project.id}/{variant.id}/storyboard.json"
            variant.export_9x16_url = f"/outputs/{project.id}/{variant.id}/mock_video_9x16.txt"
            variant.export_1x1_url = f"/outputs/{project.id}/{variant.id}/mock_video_1x1.txt"
            optimized_prompts = [
                self.prompt_optimizer.optimize(scene, brand_style=project.tone).model_dump(mode="json")
                for scene in variant.storyboard
            ]

            payload = {
                "project_id": project.id,
                "product_name": project.product_name,
                "variant_id": variant.id,
                "variant_name": variant.name,
                "angle_id": variant.angle_id,
                "angle_type": variant.angle_type,
                "selected_playbook": variant.selected_playbook,
                "status": variant.video_status,
                "title": variant.title,
                "caption": variant.caption,
                "script": variant.script,
                "storyboard": [scene.model_dump(mode="json") for scene in variant.storyboard],
                "scene_prompts": variant.scene_prompts,
                "suggested_video_model_input": optimized_prompts,
                "subtitle_text": variant.subtitles,
                "export_ratios": ["9:16", "1:1"],
                "mock_note": "Placeholder output for future real video generation provider.",
            }
            (variant_dir / "storyboard.json").write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            (variant_dir / "script.txt").write_text(
                f"{variant.name}\nAngle: {variant.angle_type or variant.angle_id}\nPlaybook: {variant.selected_playbook or 'Not specified'}\n\n{variant.script}\n\nVoiceover:\n{variant.voiceover}\n",
                encoding="utf-8",
            )
            (variant_dir / "prompts.txt").write_text(
                self._prompts_text(variant, optimized_prompts),
                encoding="utf-8",
            )
            (variant_dir / "caption.txt").write_text(
                f"Title:\n{variant.title}\n\nCaption:\n{variant.caption}\n\nCover prompt:\n{variant.cover_prompt}\n",
                encoding="utf-8",
            )
            (variant_dir / "mock_video_9x16.txt").write_text(
                self._mock_export_text(project, variant, "9:16"),
                encoding="utf-8",
            )
            (variant_dir / "mock_video_1x1.txt").write_text(
                self._mock_export_text(project, variant, "1:1"),
                encoding="utf-8",
            )
            rendered.append(variant)

        return rendered

    def _prompts_text(self, variant: Variant, optimized_prompts: list[dict]) -> str:
        lines = [f"{variant.name}", ""]
        for scene, optimized in zip(variant.storyboard, optimized_prompts, strict=False):
            lines.extend(
                [
                    f"Scene {scene.scene_number}",
                    f"Generation prompt: {scene.generation_prompt}",
                    f"Negative prompt: {scene.negative_prompt}",
                    f"Suggested video prompt: {optimized['video_prompt']}",
                    f"Camera: {optimized['camera_instruction']}",
                    f"Motion: {optimized['motion_instruction']}",
                    "",
                ]
            )
        return "\n".join(lines)

    def _mock_export_text(self, project: Project, variant: Variant, ratio: str) -> str:
        return (
            f"Mock video export\n"
            f"Project: {project.product_name}\n"
            f"Variant: {variant.name}\n"
            f"Angle: {variant.angle_type or variant.angle_id}\n"
            f"Playbook: {variant.selected_playbook or 'Not specified'}\n"
            f"Export ratio: {ratio}\n\n"
            f"Title: {variant.title}\n"
            f"Caption: {variant.caption}\n\n"
            f"Script:\n{variant.script}\n\n"
            f"Subtitles:\n" + "\n".join(variant.subtitles) + "\n"
        )
