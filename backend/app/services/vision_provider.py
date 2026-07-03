import base64
import json
from pathlib import Path
from typing import Any, Protocol

from app.models.schemas import Project, VisionAnalysis
from app.services.llm_provider import LLMProvider, build_llm_provider


class VisionProvider(Protocol):
    def analyze_files(self, project: Project) -> VisionAnalysis:
        ...


class GeminiVisionProvider:
    def __init__(self, llm_provider: LLMProvider | None = None) -> None:
        self.llm_provider = llm_provider or build_llm_provider()

    def analyze_files(self, project: Project) -> VisionAnalysis:
        prompt = self._build_prompt(project)
        parts: list[dict[str, Any]] = [{"text": prompt}]

        for uploaded_file in project.uploaded_files:
            if not uploaded_file.content_type or not uploaded_file.content_type.startswith("image/"):
                continue
            path = Path(uploaded_file.path)
            if not path.exists():
                continue
            parts.append(
                {
                    "inlineData": {
                        "mimeType": uploaded_file.content_type,
                        "data": base64.b64encode(path.read_bytes()).decode("ascii"),
                    }
                }
            )

        data = self.llm_provider.generate_json_parts(parts, temperature=0.2)
        data = self._coerce_response(data)
        return VisionAnalysis.model_validate(data)

    def _build_prompt(self, project: Project) -> str:
        payload = {
            "project": project.model_dump(mode="json"),
            "required_output_schema": {
                "detected_objects": ["string"],
                "detected_product_type": "mobile_app | skincare | fnb | ecommerce | education | general",
                "detected_visual_style": "string",
                "detected_brand_colors": ["string"],
                "detected_ui_elements": ["string"],
                "detected_text": ["string"],
                "confidence": 0.0,
                "notes": ["string"],
            },
        }
        return (
            "You are the Vision / Asset Understanding Agent for an AI ads video factory. "
            "Analyze uploaded assets when present, and use project text when images are missing. "
            "Return JSON only, no markdown. Classify product type using only one of: "
            "mobile_app, skincare, fnb, ecommerce, education, general. "
            "If image files are attached, describe visible product, UI, brand colors, visual style, and readable text. "
            "If no image is attached, infer from product name, category, description, uploaded file names, and content types.\n\n"
            f"Input:\n{json.dumps(payload, ensure_ascii=False, indent=2)}"
        )

    def _coerce_response(self, data: dict[str, Any]) -> dict[str, Any]:
        product_type = str(data.get("detected_product_type") or "general").lower().replace(" ", "_")
        aliases = {
            "app": "mobile_app",
            "mobile": "mobile_app",
            "mobileapp": "mobile_app",
            "food": "fnb",
            "food_and_beverage": "fnb",
            "f&b": "fnb",
            "education_app": "education",
            "educational": "education",
            "e-commerce": "ecommerce",
            "e_commerce": "ecommerce",
        }
        data["detected_product_type"] = aliases.get(product_type, product_type)
        if data["detected_product_type"] not in {"mobile_app", "skincare", "fnb", "ecommerce", "education", "general"}:
            data["detected_product_type"] = "general"

        confidence = data.get("confidence", 0.5)
        if isinstance(confidence, (int, float)) and confidence > 1:
            confidence = confidence / 100
        data["confidence"] = confidence

        for key in [
            "detected_objects",
            "detected_brand_colors",
            "detected_ui_elements",
            "detected_text",
            "notes",
        ]:
            value = data.get(key)
            if value is None:
                data[key] = []
            elif isinstance(value, str):
                data[key] = [value]

        data.setdefault("detected_visual_style", "not specified")
        return data
