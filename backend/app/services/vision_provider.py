from typing import Protocol

from app.models.schemas import Project, VisionAnalysis


class VisionProvider(Protocol):
    def analyze_files(self, project: Project) -> VisionAnalysis:
        ...


def _joined_project_text(project: Project) -> str:
    file_text = " ".join(
        f"{file.file_name} {file.content_type or ''}"
        for file in project.uploaded_files
    )
    return " ".join(
        [
            project.product_name,
            project.product_category or "",
            project.product_description or "",
            project.audience or "",
            file_text,
        ]
    ).lower()


class MockVisionProvider:
    def analyze_files(self, project: Project) -> VisionAnalysis:
        text = _joined_project_text(project)
        product_type = self._detect_product_type(text)
        detected_objects = self._detect_objects(text, product_type)
        ui_elements = self._detect_ui_elements(text, product_type)
        visual_style = self._visual_style(product_type, text)
        detected_text = [file.file_name for file in project.uploaded_files if file.file_name]
        notes = [
            "Mock vision analysis uses project text, category, uploaded file names, and content types.",
            f"Detected product type: {product_type}.",
        ]
        if not project.uploaded_files:
            notes.append("No uploaded assets were present, so confidence is based on text input only.")

        return VisionAnalysis(
            detected_objects=detected_objects,
            detected_product_type=product_type,
            detected_visual_style=visual_style,
            detected_brand_colors=project.brand_colors,
            detected_ui_elements=ui_elements,
            detected_text=detected_text,
            confidence=self._confidence(project, product_type),
            notes=notes,
        )

    def _detect_product_type(self, text: str) -> str:
        if any(token in text for token in ["app", "scanner", "coin", "mobile", "screenshot", "saas", "dashboard"]):
            if "education" not in text and "learning" not in text and "language" not in text:
                return "mobile_app"
        if any(token in text for token in ["coffee", "restaurant", "food", "drink", "f&b", "latte", "snack", "delivery"]):
            return "fnb"
        if any(token in text for token in ["serum", "skincare", "acne", "skin", "cleanser"]) or " cream" in text:
            return "skincare"
        if any(token in text for token in ["course", "learning", "language", "education", "lesson", "practice"]):
            return "education"
        if any(token in text for token in ["shirt", "bag", "ecommerce", "unboxing", "shop", "product"]):
            return "ecommerce"
        return "general"

    def _detect_objects(self, text: str, product_type: str) -> list[str]:
        if "coin" in text:
            return ["old coin", "phone", "coin jar"]
        if product_type == "skincare":
            return ["serum bottle", "skin texture", "bathroom routine"]
        if product_type == "fnb":
            return ["drink cup", "ice", "product close-up"]
        if product_type == "education":
            return ["phone screen", "lesson card", "practice prompt"]
        if product_type == "ecommerce":
            return ["product package", "hands-on demo", "unboxing setup"]
        if product_type == "mobile_app":
            return ["phone", "app screen", "user hand"]
        return ["product", "creator", "demo setup"]

    def _detect_ui_elements(self, text: str, product_type: str) -> list[str]:
        if product_type in {"mobile_app", "education"}:
            elements = ["mobile screen", "primary CTA button", "result screen"]
            if "scan" in text:
                elements.append("scan camera view")
            if "coin" in text:
                elements.extend(["coin detail card", "estimated reference value"])
            return elements
        return []

    def _visual_style(self, product_type: str, text: str) -> str:
        if product_type == "skincare":
            return "soft natural bathroom light, texture macro, realistic routine"
        if product_type == "fnb":
            return "bright close-up, appetizing handheld shots, taste reaction"
        if product_type == "education":
            return "clean screen recording, learner face reaction, simple overlays"
        if product_type == "ecommerce":
            return "clean unboxing table, product close-ups, practical demo"
        if product_type == "mobile_app":
            return "phone-in-hand UGC, clean app overlay, quick result reveal"
        return "natural UGC, clear product demo, simple captions"

    def _confidence(self, project: Project, product_type: str) -> float:
        score = 0.45
        if project.product_description:
            score += 0.2
        if project.product_category:
            score += 0.15
        if project.uploaded_files:
            score += 0.1
        if product_type != "general":
            score += 0.1
        return min(score, 0.95)
