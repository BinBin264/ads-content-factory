import json
from functools import lru_cache
from pathlib import Path
from typing import Any


MANIFEST_DIR = Path(__file__).resolve().parent.parent / "pipeline_manifests"
AD_VIDEO_MANIFEST = "ad_video_generation"


@lru_cache(maxsize=8)
def load_pipeline_manifest(name: str = AD_VIDEO_MANIFEST) -> dict[str, Any]:
    path = MANIFEST_DIR / f"{name}.json"
    if not path.exists():
        raise FileNotFoundError(f"Pipeline manifest not found: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Pipeline manifest must be a JSON object: {path}")
    return data


def stage_contract(manifest: dict[str, Any], stage: str) -> dict[str, Any]:
    for item in manifest.get("stages", []):
        if item.get("stage") == stage:
            return item
    return {}


def provider_requirement(manifest: dict[str, Any], tool_type: str) -> dict[str, Any]:
    for item in manifest.get("provider_requirements", []):
        if item.get("tool_type") == tool_type:
            return item
    return {}
