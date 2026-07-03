from typing import Any

from app.models.schemas import ProductIntelligenceBrief, Project


def compact_project_context(project: Project) -> dict[str, Any]:
    return {
        "product_name": project.product_name,
        "product_category": project.product_category,
        "product_description": project.product_description,
        "audience": project.audience,
        "goal": project.goal,
        "platform": project.platform,
        "duration": project.duration,
        "tone": project.tone,
        "cta": project.cta,
        "claims_to_avoid": project.claims_to_avoid,
        "brand_colors": project.brand_colors,
        "uploaded_files": [file.file_name for file in project.uploaded_files],
    }


def compact_intelligence_context(intelligence: ProductIntelligenceBrief) -> dict[str, Any]:
    return {
        "detected_product": intelligence.detected_product,
        "product_category": intelligence.product_category,
        "product_type": intelligence.product_type,
        "core_use_case": intelligence.core_use_case,
        "primary_audience": intelligence.primary_audience,
        "audience_segments": intelligence.target_audience_segments,
        "pain_points": intelligence.pain_points,
        "emotional_triggers": intelligence.emotional_triggers,
        "functional_benefits": intelligence.functional_benefits,
        "proof_points": intelligence.proof_points,
        "demo_moments": intelligence.demo_moments,
        "visual_assets_detected": intelligence.visual_assets_detected,
        "brand_style_notes": intelligence.brand_style_notes,
        "safe_claims": intelligence.safe_claims,
        "claims_to_avoid": intelligence.claims_to_avoid,
        "recommended_hooks": intelligence.recommended_hooks,
        "recommended_cta": intelligence.recommended_cta,
        "recommended_ad_playbooks": [
            {
                "playbook_id": playbook.playbook_id,
                "name": playbook.name,
                "structure": playbook.structure,
                "scene_formula": playbook.scene_formula,
            }
            for playbook in intelligence.recommended_ad_playbooks[:2]
        ],
    }
