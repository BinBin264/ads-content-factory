import json
from pathlib import Path
from typing import Protocol

from app.config import OUTPUTS_DIR, ensure_app_dirs
from app.models.schemas import Project, Variant


class VideoProvider(Protocol):
    def render_mock(self, project: Project, variants: list[Variant]) -> list[Variant]:
        ...


class MockVideoProvider:
    def __init__(self, outputs_dir: Path = OUTPUTS_DIR) -> None:
        self.outputs_dir = outputs_dir
        ensure_app_dirs()

    def render_mock(self, project: Project, variants: list[Variant]) -> list[Variant]:
        project_dir = self.outputs_dir / project.id
        project_dir.mkdir(parents=True, exist_ok=True)

        rendered: list[Variant] = []
        for variant in variants:
            variant.video_status = "ready"
            variant.mock_video_url = f"/outputs/{project.id}/{variant.id}_mock_video.json"
            variant.export_9x16_url = f"/outputs/{project.id}/{variant.id}_9x16.txt"
            variant.export_1x1_url = f"/outputs/{project.id}/{variant.id}_1x1.txt"

            payload = {
                "project_id": project.id,
                "variant_id": variant.id,
                "status": variant.video_status,
                "title": variant.title,
                "caption": variant.caption,
                "script": variant.script,
                "storyboard": [scene.model_dump(mode="json") for scene in variant.storyboard],
                "mock_note": "Placeholder output for future real video generation provider.",
            }
            (project_dir / f"{variant.id}_mock_video.json").write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            (project_dir / f"{variant.id}_9x16.txt").write_text(
                f"Mock 9:16 video export for {variant.title}\n\n{variant.script}\n",
                encoding="utf-8",
            )
            (project_dir / f"{variant.id}_1x1.txt").write_text(
                f"Mock 1:1 video export for {variant.title}\n\n{variant.script}\n",
                encoding="utf-8",
            )
            rendered.append(variant)

        return rendered
