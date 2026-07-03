import json

from app.models.schemas import CharacterBible, CharacterReferencePrompt, CreativeAngle, ProductIntelligenceBrief, Variant
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

        prompts = [CharacterReferencePrompt.model_validate(item) for item in raw_prompts]
        found_ids = {prompt.reference_id for prompt in prompts}
        missing_ids = REQUIRED_REFERENCE_IDS - found_ids
        if missing_ids:
            raise ValueError(f"Gemini character reference prompts missing required ids: {', '.join(sorted(missing_ids))}")
        return prompts

    def _build_prompt(
        self,
        character_bible: CharacterBible,
        product_intelligence: ProductIntelligenceBrief,
        creative_angle: CreativeAngle,
        variant: Variant,
    ) -> str:
        return (
            "You are an AI image prompt engineer.\n\n"
            "Create a character reference pack based on this Character Bible.\n\n"
            f"Character Bible:\n{json.dumps(character_bible.model_dump(mode='json'), ensure_ascii=False, indent=2)}\n\n"
            f"Product Intelligence:\n{json.dumps(product_intelligence.model_dump(mode='json'), ensure_ascii=False, indent=2)}\n\n"
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
            "- Every prompt must describe the same character exactly.\n"
            "- Repeat face, hair, facial hair, age, outfit, body type, and setting in every prompt.\n"
            "- Prompts must be realistic UGC style.\n"
            "- Avoid complex text, logos, or UI on screen.\n"
            "- Include natural lighting and simple background.\n"
            "- Negative prompt must prevent changed identity, distorted hands, extra fingers, different clothes, different face.\n"
            "- For phone screens, keep the screen blank or clean for later overlay.\n"
        )
