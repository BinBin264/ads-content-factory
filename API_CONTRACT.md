# API Contract

Shared project shape for backend and frontend integration.

```json
{
  "project": {
    "id": "project_001",
    "product_name": "Coin Scanner App",
    "product_category": "mobile app",
    "product_description": "An app that scans old coins and shows coin details and estimated reference value.",
    "audience": "people who find old coins at home",
    "goal": "app_install",
    "platform": "tiktok",
    "duration": "20s",
    "tone": "UGC, natural, realistic",
    "cta": "Download now",
    "claims_to_avoid": ["guaranteed value", "100% accurate appraisal"],
    "brand_colors": ["#1E88E5", "#FFFFFF"],
    "uploaded_files": [],
    "product_intelligence": {},
    "product_brief": {},
    "creative_angles": [],
    "variants": [],
    "created_at": "2026-07-02T00:00:00",
    "updated_at": "2026-07-02T00:00:00"
  }
}
```

For `POST /api/projects`, the frontend sends multipart form data. Array fields are sent as repeated fields:

```text
claims_to_avoid=guaranteed value
claims_to_avoid=100% accurate appraisal
brand_colors=#1E88E5
brand_colors=#FFFFFF
```

The backend also accepts comma, semicolon, or newline-separated values for compatibility, then stores and returns arrays.

## Product Brief Shape

`POST /api/projects/{project_id}/analyze` returns:

```json
{
  "product_intelligence": {},
  "product_brief": {},
  "vision_analysis": {}
}
```

`product_intelligence` shape:

```json
{
  "detected_product": "Coin Scanner App",
  "product_category": "mobile app",
  "product_type": "mobile_app",
  "core_use_case": "Scan old coins, identify coin details, and view estimated reference value.",
  "target_audience_segments": ["people who find old coins at home"],
  "primary_audience": "people who find old coins at home",
  "pain_points": ["Users do not know whether an old coin is worth researching."],
  "emotional_triggers": ["curiosity", "surprise"],
  "functional_benefits": ["scan old coins", "identify coin details"],
  "proof_points": ["screen demo", "result screen"],
  "demo_moments": ["Show the object or problem", "Open the app", "Use the key feature", "Show the result screen"],
  "visual_assets_detected": ["old coin", "phone"],
  "brand_style_notes": "phone-in-hand UGC",
  "safe_claims": ["estimated reference value"],
  "claims_to_avoid": ["guaranteed value", "100% accurate appraisal"],
  "recommended_ad_playbooks": [],
  "recommended_video_formats": ["9:16 UGC app demo"],
  "recommended_hooks": ["I almost spent this old coin..."],
  "recommended_cta": "Download now",
  "confidence_score": 0.85
}
```

`product_brief` compatibility shape:

```json
{
  "product_name": "Coin Scanner App",
  "category": "mobile app",
  "product_type": "Mobile coin identification app",
  "short_description": "An app that helps users scan old coins, identify coin details, and view estimated reference value.",
  "target_audience": ["People who find old coins at home, casual collectors, adults with coin jars."],
  "main_problem": "People find old coins at home but do not know what they are, whether they are common, or what details to look up.",
  "main_benefit": "The app helps users scan a coin, identify key details, and view an estimated reference value for research.",
  "emotional_triggers": ["curiosity", "surprise", "nostalgia", "discovery"],
  "functional_benefits": ["coin scanning flow", "coin detail lookup", "estimated reference value"],
  "proof_elements": ["phone camera scanning an old coin", "app result screen with coin details"],
  "safe_claims": ["Helps identify coin details", "Shows estimated reference value for research"],
  "claims_to_avoid": ["guaranteed value", "100% accurate appraisal"],
  "recommended_visual_style": "Natural UGC at a kitchen table or desk, old coin jar, phone-in-hand scan demo.",
  "recommended_ad_formats": ["Found coin curiosity -> app scan demo -> estimated reference result -> CTA"]
}
```
