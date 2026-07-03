import json

from app.models.schemas import CharacterBible, CharacterPlan, CreativeAngle, ProductIntelligenceBrief, Variant
from app.services.intelligence_context import compact_intelligence_context
from app.services.llm_provider import LLMProvider, build_llm_provider


IDENTITY_LOCK_PROMPT = (
    "Use the same character from the generated character reference images. Preserve face, hairstyle, "
    "facial hair, age, skin tone, body type, outfit, and setting. Do not change identity across scenes."
)


class GeminiCharacterPlanner:
    def __init__(self, llm_provider: LLMProvider | None = None) -> None:
        self.llm_provider = llm_provider or build_llm_provider()

    def plan(
        self,
        *,
        product_intelligence: ProductIntelligenceBrief,
        creative_angle: CreativeAngle,
        variant: Variant,
        platform: str,
        tone: str,
    ) -> tuple[CharacterPlan, CharacterBible]:
        prompt = self._build_prompt(product_intelligence, creative_angle, variant, platform, tone)
        data = self.llm_provider.generate_json(prompt, temperature=0.35)
        raw_plan = data.get("character_plan")
        if not isinstance(raw_plan, dict):
            raise ValueError("Gemini character planner response must include character_plan")

        character_plan = CharacterPlan.model_validate(raw_plan)
        character_bible = self._build_character_bible(character_plan)
        return character_plan, character_bible

    def _build_character_bible(self, character_plan: CharacterPlan) -> CharacterBible:
        base_prompt = (
            f"{character_plan.recommended_character_type}. {character_plan.gender}, {character_plan.age_range}, "
            f"{character_plan.ethnicity_or_look}. Face: {character_plan.face_details}. Hair: {character_plan.hair}. "
            f"Facial hair: {character_plan.facial_hair}. Body type: {character_plan.body_type}. "
            f"Outfit: {character_plan.outfit}. Setting: {character_plan.setting}. "
            f"Props: {', '.join(character_plan.props)}. Personality: {', '.join(character_plan.personality)}. "
            f"Speaking style: {character_plan.speaking_style}. Visual style: {character_plan.visual_style}."
        )
        display_name = character_plan.recommended_character_type.strip() or "Main UGC character"
        return CharacterBible(
            display_name=display_name,
            role=character_plan.role_in_ad,
            gender=character_plan.gender,
            age_range=character_plan.age_range,
            ethnicity_or_look=character_plan.ethnicity_or_look,
            face_details=character_plan.face_details,
            hair=character_plan.hair,
            facial_hair=character_plan.facial_hair,
            body_type=character_plan.body_type,
            outfit=character_plan.outfit,
            props=character_plan.props,
            setting=character_plan.setting,
            personality=character_plan.personality,
            speaking_style=character_plan.speaking_style,
            visual_style=character_plan.visual_style,
            consistency_locks=character_plan.consistency_locks,
            negative_identity_changes=character_plan.negative_identity_changes,
            base_prompt=base_prompt,
            identity_lock_prompt=IDENTITY_LOCK_PROMPT,
        )

    def _build_prompt(
        self,
        product_intelligence: ProductIntelligenceBrief,
        creative_angle: CreativeAngle,
        variant: Variant,
        platform: str,
        tone: str,
    ) -> str:
        return (
            "You are a casting director for AI-generated UGC video ads.\n\n"
            "Your job is to create the most suitable main character for this specific ad script.\n\n"
            "Input:\n"
            f"Product Intelligence:\n{json.dumps(compact_intelligence_context(product_intelligence), ensure_ascii=False, indent=2)}\n\n"
            f"Creative Angle:\n{json.dumps(creative_angle.model_dump(mode='json'), ensure_ascii=False, indent=2)}\n\n"
            f"Script:\n{variant.script}\n\n"
            f"Platform:\n{platform}\n\n"
            f"Tone:\n{tone}\n\n"
            "Return JSON only:\n"
            "{\n"
            '  "character_plan": {\n'
            '    "recommended_character_type": "",\n'
            '    "reason": "",\n'
            '    "gender": "",\n'
            '    "age_range": "",\n'
            '    "ethnicity_or_look": "",\n'
            '    "face_details": "",\n'
            '    "hair": "",\n'
            '    "facial_hair": "",\n'
            '    "body_type": "",\n'
            '    "outfit": "",\n'
            '    "setting": "",\n'
            '    "props": [],\n'
            '    "personality": [],\n'
            '    "speaking_style": "",\n'
            '    "visual_style": "",\n'
            '    "role_in_ad": "",\n'
            '    "consistency_locks": [],\n'
            '    "negative_identity_changes": []\n'
            "  }\n"
            "}\n\n"
            "Rules:\n"
            "- Create a character that fits the product, audience, creative angle, and script situation.\n"
            "- Do not use a preset model library.\n"
            "- Do not create random characters.\n"
            "- For UGC app ads, use one relatable main actor.\n"
            "- For family discovery or old objects, prefer a mature, trustworthy, warm character.\n"
            "- For skincare, prefer a natural lifestyle reviewer in a bathroom or bedroom routine setting.\n"
            "- For F&B, prefer an expressive creator or office/student persona depending on audience.\n"
            "- For education apps, prefer a student or young professional.\n"
            "- Keep the character simple enough to reproduce across multiple scenes.\n"
            "- Include outfit, setting, props, and consistency locks.\n"
            "- The character must be designed for future reference image generation.\n"
            "- For Coin Scanner App family discovery/nostalgia angles, prefer age_range 35-45, warm kitchen dining table, neutral beige casual shirt, old coin, smartphone, wooden coin box.\n"
        )
