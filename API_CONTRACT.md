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
    "brand_colors": [],
    "uploaded_files": [],
    "vision_analysis": {},
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
```

The backend also accepts comma, semicolon, or newline-separated values for compatibility, then stores and returns arrays. `brand_colors` remains a backend compatibility field but is no longer a primary frontend input; brand colors should usually be inferred from uploads, description, and vision analysis.

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

## Variant Shape

`POST /api/projects/{project_id}/generate-variants` returns `Variant[]`. Legacy fields are kept for compatibility and each new variant includes `production_package`.

```json
{
  "id": "variant_001",
  "angle_id": "angle_001",
  "name": "Discovery Variant",
  "duration": "20s",
  "format": "9:16",
  "hook": "I found this old coin at home...",
  "script": "Scene 1...",
  "storyboard": [],
  "scene_prompts": [],
  "voiceover": "",
  "subtitles": [],
  "title": "",
  "caption": "",
  "cover_prompt": "",
  "production_package": {},
  "selected_playbook": "Discovery & Reveal",
  "angle_type": "storytelling",
  "video_status": "draft",
  "video_url": null,
  "export_9x16_url": null,
  "export_1x1_url": null,
  "export_package_url": null
}
```

Allowed `video_status` values:

```text
draft, package_exported, rendering, ready, failed
```

## Production Package Shape

`Variant.production_package`:

```json
{
  "variant_id": "variant_001",
  "creative_angle_id": "angle_001",
  "character_plan": {},
  "character_bible": {},
  "character_reference_prompts": [],
  "production_scenes": [],
  "edit_plan": {},
  "app_ui_overlay_notes": "",
  "asset_checklist": [],
  "compliance_notes": [],
  "render_sequence": []
}
```

`CharacterPlan`:

```json
{
  "recommended_character_type": "Warm family UGC reviewer",
  "reason": "The script is about discovering an old coin at home.",
  "gender": "female",
  "age_range": "35-45",
  "ethnicity_or_look": "relatable everyday adult",
  "face_details": "natural friendly face",
  "hair": "simple natural hairstyle",
  "facial_hair": "none",
  "body_type": "average",
  "outfit": "neutral beige casual shirt",
  "setting": "warm kitchen dining table",
  "props": ["old coin", "smartphone", "wooden coin box"],
  "personality": ["curious", "nostalgic", "trustworthy"],
  "speaking_style": "natural UGC, conversational",
  "visual_style": "realistic phone-shot UGC",
  "role_in_ad": "main actor and product demonstrator",
  "consistency_locks": ["same face", "same hairstyle", "same outfit", "same kitchen setting"],
  "negative_identity_changes": ["different person", "changed face", "different outfit"]
}
```

`CharacterBible`:

```json
{
  "character_id": "character_001",
  "display_name": "Warm family UGC reviewer",
  "role": "main actor and product demonstrator",
  "gender": "female",
  "age_range": "35-45",
  "ethnicity_or_look": "relatable everyday adult",
  "face_details": "natural friendly face",
  "hair": "simple natural hairstyle",
  "facial_hair": "none",
  "body_type": "average",
  "outfit": "neutral beige casual shirt",
  "props": ["old coin", "smartphone", "wooden coin box"],
  "setting": "warm kitchen dining table",
  "personality": ["curious", "nostalgic", "trustworthy"],
  "speaking_style": "natural UGC, conversational",
  "visual_style": "realistic phone-shot UGC",
  "consistency_locks": ["same face", "same hairstyle", "same outfit", "same kitchen setting"],
  "negative_identity_changes": ["different person", "changed face", "different outfit"],
  "base_prompt": "Full reusable identity prompt.",
  "identity_lock_prompt": "Use the same character from the generated character reference images. Preserve face, hairstyle, facial hair, age, skin tone, body type, outfit, and setting. Do not change identity across scenes."
}
```

`CharacterReferencePrompt`:

```json
{
  "reference_id": "front_portrait",
  "purpose": "Master identity reference",
  "aspect_ratio": "4:5",
  "prompt": "Realistic UGC portrait of the same character...",
  "negative_prompt": "changed face, different outfit, distorted hands, extra fingers",
  "notes": "Use as master reference image."
}
```

Required reference ids:

```text
front_portrait
three_quarter_portrait
seated_in_main_setting
holding_key_object
holding_phone_or_cta_pose
```

`ProductionScene`:

```json
{
  "scene_number": 3,
  "duration_seconds": 5,
  "creative_objective": "Product/app demo proof",
  "shot_type": "over-the-shoulder close-up",
  "camera_angle": "phone and coin clearly visible",
  "generation_mode": "image_to_video",
  "required_reference_assets": ["front_portrait", "holding_key_object", "app screenshot"],
  "visual_description": "Same character scans an old coin at the kitchen table.",
  "action_description": "The phone moves closer to the coin and the coin is rotated slightly.",
  "keyframe_prompt": "Production-ready image prompt.",
  "video_prompt": "Production-ready image-to-video prompt with identity lock.",
  "motion_instruction": "Slow natural hand movement, subtle camera shake.",
  "consistency_instruction": "Preserve same character, outfit, setting, phone, and coin.",
  "negative_prompt": "different person, changed face, unreadable app text",
  "ui_overlay_plan": [],
  "voiceover_line": "I scanned both sides in the app.",
  "on_screen_text": "Scanning coin...",
  "transition": "Match cut to result.",
  "safety_notes": "Use estimated reference value only."
}
```

Allowed `generation_mode` values:

```text
text_to_image, image_to_video, reference_to_video, overlay_only
```

`UIOverlayItem`:

```json
{
  "overlay_type": "disclaimer",
  "text": "Estimated reference value only. Actual value may vary.",
  "start_time": "0:03",
  "end_time": "0:05",
  "position": "bottom",
  "style_notes": "Small readable high-contrast caption.",
  "safety_notes": "Required value disclaimer."
}
```

Allowed `overlay_type` values:

```text
app_screen, subtitle, cta, disclaimer, logo, price_label, button, highlight
```

`EditPlan`:

```json
{
  "total_duration": "20s",
  "pacing_notes": "Fast UGC hook, clear demo, short CTA.",
  "music_direction": "Light curiosity-driven background music.",
  "subtitle_style": "Bold readable captions, high contrast.",
  "cut_sequence": ["Scene 1 hook", "Scene 2 setup", "Scene 3 demo", "Scene 4 CTA"],
  "export_ratios": ["9:16", "1:1"],
  "required_post_production_steps": ["Add UI overlays", "Add subtitles", "Add logo/CTA end card"],
  "platform_notes": "TikTok/Reels/Shorts vertical delivery."
}
```

## Export Production Package

`POST /api/projects/{project_id}/export-production-package`

Response: `Project`

Behavior:

- Requires existing variants.
- Requires every exported variant to have `production_package`.
- Creates `backend/app/outputs/{project_id}/{variant_id}/`.
- Writes:
  - `character_bible.json`
  - `character_reference_prompts.txt`
  - `production_scenes.json`
  - `keyframe_prompts.txt`
  - `video_prompts.txt`
  - `ui_overlay_plan.txt`
  - `edit_plan.txt`
  - `script.txt`
  - `storyboard.json`
  - `caption.txt`
  - `production_package.zip`
- Sets `variant.video_status = "package_exported"`.
- Sets `variant.export_package_url` to the zip URL.
- Does not create video files, placeholder video, or mock video output.

Error responses:

```json
{"detail": "Generate variants before exporting production package."}
```

```json
{"detail": "Variant is missing production_package. Generate variants again."}
```

## Render Video

`POST /api/projects/{project_id}/render`

Response: `Project`

Behavior:

- Calls only the configured real video provider.
- Does not create fake video files.
- Does not create placeholder video files.
- Does not create `mock_video_9x16.txt` or `mock_video_1x1.txt`.

If provider env is missing:

```json
{"detail": "Video provider is not configured. Set VIDEO_PROVIDER_NAME and VIDEO_PROVIDER_API_KEY."}
```

If provider env exists but no adapter is implemented:

```json
{"detail": "Provider is configured but render adapter is not implemented yet."}
```
