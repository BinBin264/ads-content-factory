import json
from typing import Any

from app.models.schemas import CharacterBible, CharacterReferencePrompt, CreativeAngle, CreativePlan, ProductIntelligenceBrief, Project, Variant, VariantDirection
from app.services.intelligence_context import compact_intelligence_context
from app.services.llm_provider import LLMProvider, build_llm_provider


REQUIRED_REFERENCE_IDS = {
    "front_portrait",
    "three_quarter_portrait",
    "seated_in_main_setting",
    "holding_key_object",
    "holding_phone_or_cta_pose",
}


class GeminiCharacterReferenceGenerator:
    def __init__(self, llm_provider: LLMProvider | None = None) -> None:
        self.llm_provider = llm_provider or build_llm_provider()

    def generate(
        self,
        *,
        character_bible: CharacterBible,
        product_intelligence: ProductIntelligenceBrief,
        creative_angle: CreativeAngle,
        variant: Variant,
    ) -> list[CharacterReferencePrompt]:
        prompt = self._build_prompt(character_bible, product_intelligence, creative_angle, variant)
        data = self.llm_provider.generate_json(prompt, temperature=0.35)
        raw_prompts = data.get("character_reference_prompts")
        if not isinstance(raw_prompts, list):
            raise ValueError("Gemini character reference response must include character_reference_prompts")

        prompts = [CharacterReferencePrompt.model_validate(self._coerce_prompt(item, character_bible.base_prompt)) for item in raw_prompts]
        found_ids = {prompt.reference_id for prompt in prompts}
        missing_ids = REQUIRED_REFERENCE_IDS - found_ids
        if missing_ids:
            raise ValueError(f"Gemini character reference prompts missing required ids: {', '.join(sorted(missing_ids))}")
        return prompts

    def generate_from_creative_plan(
        self,
        *,
        character_bible: CharacterBible,
        project: Project,
        creative_plan: CreativePlan,
        variant_direction: VariantDirection,
        variant: Variant,
    ) -> list[CharacterReferencePrompt]:
        prompt = self._build_creative_plan_prompt(character_bible, project, creative_plan, variant_direction, variant)
        data = self.llm_provider.generate_json(prompt, temperature=0.35)
        raw_prompts = data.get("character_reference_prompts")
        if not isinstance(raw_prompts, list):
            raise ValueError("Gemini character reference response must include character_reference_prompts")

        prompts = [CharacterReferencePrompt.model_validate(self._coerce_prompt(item, character_bible.base_prompt)) for item in raw_prompts]
        found_ids = {prompt.reference_id for prompt in prompts}
        missing_ids = REQUIRED_REFERENCE_IDS - found_ids
        if missing_ids:
            raise ValueError(f"Gemini character reference prompts missing required ids: {', '.join(sorted(missing_ids))}")
        return prompts

    def _coerce_prompt(self, item: Any, identity_anchor: str) -> dict[str, str]:
        if not isinstance(item, dict):
            raise ValueError("Each character reference prompt must be an object")

        prompt = str(item.get("prompt") or "").strip()
        if identity_anchor and identity_anchor not in prompt:
            prompt = f"{identity_anchor} {prompt}".strip()

        return {
            "reference_id": str(item.get("reference_id") or "").strip(),
            "purpose": str(item.get("purpose") or "Character reference").strip(),
            "aspect_ratio": str(item.get("aspect_ratio") or "9:16").strip(),
            "prompt": prompt,
            "negative_prompt": str(
                item.get("negative_prompt")
                or "changed identity, different face, different outfit, distorted hands, extra fingers, blurry, low quality"
            ).strip(),
            "notes": str(item.get("notes") or "").strip(),
        }

    def _build_prompt(
        self,
        character_bible: CharacterBible,
        product_intelligence: ProductIntelligenceBrief,
        creative_angle: CreativeAngle,
        variant: Variant,
    ) -> str:
        return (
            "You are an AI image prompt engineer.\n\n"
            "Create a character reference pack for ONE single UGC actor based on this Character Bible.\n\n"
            f"Character Bible:\n{json.dumps(character_bible.model_dump(mode='json'), ensure_ascii=False, indent=2)}\n\n"
            f"Identity anchor that must stay unchanged in every prompt:\n{character_bible.base_prompt}\n\n"
            f"Product Intelligence:\n{json.dumps(compact_intelligence_context(product_intelligence), ensure_ascii=False, indent=2)}\n\n"
            f"Creative Angle:\n{json.dumps(creative_angle.model_dump(mode='json'), ensure_ascii=False, indent=2)}\n\n"
            f"Script:\n{variant.script}\n\n"
            "Return JSON only:\n"
            "{\n"
            '  "character_reference_prompts": [\n'
            '    {"reference_id": "front_portrait", "purpose": "Master identity reference", "aspect_ratio": "4:5", "prompt": "", "negative_prompt": "", "notes": ""},\n'
            '    {"reference_id": "three_quarter_portrait", "purpose": "3/4 face reference", "aspect_ratio": "4:5", "prompt": "", "negative_prompt": "", "notes": ""},\n'
            '    {"reference_id": "seated_in_main_setting", "purpose": "Same character in main ad setting", "aspect_ratio": "9:16", "prompt": "", "negative_prompt": "", "notes": ""},\n'
            '    {"reference_id": "holding_key_object", "purpose": "Same character holding key object or product", "aspect_ratio": "9:16", "prompt": "", "negative_prompt": "", "notes": ""},\n'
            '    {"reference_id": "holding_phone_or_cta_pose", "purpose": "Same character holding phone or CTA pose", "aspect_ratio": "9:16", "prompt": "", "negative_prompt": "", "notes": ""}\n'
            "  ]\n"
            "}\n\n"
            "Rules:\n"
            "- These are NOT different characters. They are multiple reference images of the same actor.\n"
            "- Start every prompt with the same identity anchor, then add only the reference-specific pose, framing, and prop.\n"
            "- Repeat face, hair, facial hair, age, skin tone, outfit, body type, and setting in every prompt.\n"
            "- Keep outfit and setting unchanged unless the Character Bible explicitly says otherwise.\n"
            "- Change only camera angle, pose, hand position, expression, and whether the actor holds the coin/phone.\n"
            "- Prompts must be realistic UGC style and should not read like separate story scenes.\n"
            "- Avoid complex text, logos, or UI on screen.\n"
            "- Include natural lighting and simple background.\n"
            "- Negative prompt must prevent changed identity, distorted hands, extra fingers, different clothes, different face.\n"
            "- For phone screens, keep the screen blank or clean for later overlay.\n"
        )

    def _build_creative_plan_prompt(
        self,
        character_bible: CharacterBible,
        project: Project,
        creative_plan: CreativePlan,
        variant_direction: VariantDirection,
        variant: Variant,
    ) -> str:
        context = {
            "project": {
                "product_name": project.product_name,
                "product_category": project.product_category,
                "product_description": project.product_description,
                "audience": project.audience,
                "platform": project.platform,
                "tone": project.tone,
                "uploaded_files": [item.file_name for item in project.uploaded_files],
            },
            "creative_plan": creative_plan.model_dump(mode="json"),
            "variant_direction": variant_direction.model_dump(mode="json"),
            "variant": {
                "name": variant.name,
                "hook": variant.hook,
                "script_summary": variant.script_summary,
                "timeline": [scene.model_dump(mode="json") for scene in variant.timeline],
            },
        }
        return (
            "You are an AI image prompt engineer.\n\n"
            "Create a character reference pack for ONE single UGC actor based on this Character Bible. "
            "These references are used to keep the actor consistent before scene keyframes and video generation.\n\n"
            f"Character Bible:\n{json.dumps(character_bible.model_dump(mode='json'), ensure_ascii=False, indent=2)}\n\n"
            f"Identity anchor that must stay unchanged in every prompt:\n{character_bible.base_prompt}\n\n"
            f"Creative context:\n{json.dumps(context, ensure_ascii=False, indent=2)}\n\n"
            "Return JSON only:\n"
            "{\n"
            '  "character_reference_prompts": [\n'
            '    {"reference_id": "front_portrait", "purpose": "Master identity reference", "aspect_ratio": "4:5", "prompt": "", "negative_prompt": "", "notes": ""},\n'
            '    {"reference_id": "three_quarter_portrait", "purpose": "3/4 face reference", "aspect_ratio": "4:5", "prompt": "", "negative_prompt": "", "notes": ""},\n'
            '    {"reference_id": "seated_in_main_setting", "purpose": "Same character in main ad setting", "aspect_ratio": "9:16", "prompt": "", "negative_prompt": "", "notes": ""},\n'
            '    {"reference_id": "holding_key_object", "purpose": "Same character holding key object or product", "aspect_ratio": "9:16", "prompt": "", "negative_prompt": "", "notes": ""},\n'
            '    {"reference_id": "holding_phone_or_cta_pose", "purpose": "Same character holding phone or CTA pose", "aspect_ratio": "9:16", "prompt": "", "negative_prompt": "", "notes": ""}\n'
            "  ]\n"
            "}\n\n"
            "Rules:\n"
            "- These are NOT different characters. They are multiple reference images of the same actor.\n"
            "- Start every prompt with the same identity anchor, then add only pose, framing, camera angle, and prop changes.\n"
            "- Keep face, hair, facial hair, age, skin tone, outfit, body type, and setting unchanged in every prompt.\n"
            "- Change only camera angle, pose, hand position, expression, and whether the actor holds the key object or phone.\n"
            "- Prompts must be realistic UGC style and should not read like separate story scenes.\n"
            "- Avoid complex text, logos, or UI on screen.\n"
            "- For phone screens, keep the screen blank or clean for later overlay.\n"
            "- Negative prompt must prevent changed identity, distorted hands, extra fingers, different clothes, and different face.\n"
        )
