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
    "creative_plan": {},
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

## Creative Plan Shape

Primary planning endpoint:

```text
POST /api/projects/{project_id}/creative-plan
```

Response: `CreativePlan`

Legacy compatibility endpoint:

```text
POST /api/projects/{project_id}/analyze
```

Response:

```json
{
  "creative_plan": {},
  "product_intelligence": {},
  "product_brief": {},
  "vision_analysis": {}
}
```

`creative_plan` is the primary production planning artifact. The current frontend uses `/creative-plan`; `/analyze` remains only for older integrations that still expect `product_intelligence`, `product_brief`, and `vision_analysis` in the same response.

```json
{
  "product_truth": "Coin Scanner App helps users scan old coins, identify details, and view estimated reference value for research.",
  "audience_pain": "People find old coins at home but do not know what they are or whether they are worth researching.",
  "main_message": "Scan the coin and get useful details in seconds.",
  "safe_claims": ["estimated reference value"],
  "forbidden_claims": ["guaranteed value", "100% accurate appraisal"],
  "cta": "Download now",
  "visual_style": "Natural UGC at a table, phone-in-hand scan demo, readable app UI overlays.",
  "variant_directions": [
    {
      "id": "direction_001",
      "name": "Storytelling / Problem-led",
      "hypothesis": "A familiar found-at-home story can raise hook retention.",
      "creative_angle": "I found an old coin and wanted to know what it was.",
      "best_for_metric": "hook_rate"
    },
    {
      "id": "direction_002",
      "name": "Product Demo / Benefit-led",
      "hypothesis": "A direct scan demo can improve install intent.",
      "creative_angle": "Scan the coin, see details, then research the estimated reference value.",
      "best_for_metric": "conversion_rate"
    }
  ]
}
```

`product_intelligence`, `product_brief`, and `creative_angles` are kept as compatibility fields. They are derived from `creative_plan` and should not be treated as separate planning phases. `POST /api/projects/{project_id}/angles` is deprecated and should not be used by the main UI.

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

`POST /api/projects/{project_id}/generate-variants` returns `Variant[]`. The core path uses `project.creative_plan.variant_directions` directly and generates exactly two variants: Storytelling / Problem-led and Product Demo / Benefit-led. `angle_ids` is accepted for request compatibility but is ignored by the new main flow. Legacy fields are kept for compatibility and each new variant includes `production_package` and `generation_pipeline`.

```json
{
  "id": "variant_001",
  "angle_id": "angle_001",
  "name": "Discovery Variant",
  "hypothesis": "A familiar found-at-home story can raise hook retention.",
  "target_metric": "hook_rate",
  "duration": "20s",
  "format": "9:16",
  "hook": "I found this old coin at home...",
  "script_summary": "Story-led UGC coin discovery ad.",
  "timeline": [],
  "script": "Scene 1...",
  "storyboard": [],
  "scene_prompts": [],
  "voiceover": "",
  "subtitles": [],
  "title": "",
  "caption": "",
  "cover_prompt": "",
  "production_package": {},
  "generation_pipeline": {},
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
app_screen_overlay, text_overlay, subtitle, cta, disclaimer, logo, price_label, button, highlight
```

`app_screen` may appear only in old saved projects for compatibility. New generation should use `app_screen_overlay`.

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

## Generation Pipeline Shape

`Variant.generation_pipeline`:

```json
{
  "pipeline_id": "pipeline_001",
  "variant_id": "variant_001",
  "pipeline_name": "ad_video_generation",
  "pipeline_version": "1.0",
  "objective": "Turn the Creative Plan, variant direction, timeline, storyboard, and production package into a connected step-by-step video creation workflow.",
  "status": "in_progress",
  "source_artifacts": [],
  "stage_contracts": [],
  "provider_contracts": [],
  "assets": [],
  "steps": []
}
```

`source_artifacts` explains how prior phases feed the workflow:

```json
{
  "artifact_key": "creative_plan",
  "label": "Creative Plan",
  "source_phase": "creative_plan",
  "description": "Used to decide product truth, audience pain, safe claims, CTA, visual style, and variant directions."
}
```

`stage_contracts` are loaded from `backend/app/pipeline_manifests/ad_video_generation.json`. Each stage documents:

```json
{
  "stage": "video_clip",
  "label": "Image-to-video clips",
  "purpose": "Animate each approved keyframe into a short scene clip while preserving identity, product context, and timing.",
  "required_artifacts_in": ["scene_keyframe_images", "character_reference_images", "production_package.production_scenes"],
  "produces": ["raw_scene_clips"],
  "tool_type": "video_generation",
  "provider_capability": "video_generation",
  "review_focus": [],
  "success_criteria": []
}
```

`provider_contracts` describe the current provider/manual path. They do not create mock output:

```json
{
  "tool_type": "video_generation",
  "capability": "video_generation",
  "provider_name": "manual_web_tool",
  "configured": false,
  "adapter_status": "configured_no_adapter",
  "status": "missing_env",
  "manual_supported": true,
  "required_env": ["VIDEO_PROVIDER_NAME", "VIDEO_PROVIDER_API_KEY"],
  "recommended_manual_tools": ["Kling image-to-video", "Runway", "Veo", "Luma"],
  "notes": "Used for image-to-video scene clips."
}
```

`PipelineAsset`:

```json
{
  "asset_id": "asset_001",
  "asset_key": "scene_1_keyframe",
  "asset_type": "image",
  "label": "Scene 1 keyframe",
  "url": "/outputs/project_001/variant_001/assets/scene_1_keyframe.png",
  "path": "backend/app/outputs/project_001/variant_001/assets/scene_1_keyframe.png",
  "source": "uploaded_by_user",
  "source_step_id": "scene_1_keyframe",
  "metadata": {}
}
```

Allowed asset types:

```text
image, video, audio, app_screenshot, subtitle, json, zip
```

Allowed asset sources:

```text
uploaded_by_user, generated_by_provider, project_upload, exported
```

`PipelineStep` contains executable manual and provider instructions:

```json
{
  "step_id": "scene_1_keyframe",
  "step_number": 6,
  "stage": "scene_keyframe",
  "stage_label": "Scene keyframes",
  "stage_purpose": "Create one controllable still image per production scene before video generation.",
  "title": "Generate scene 1 keyframe",
  "goal": "Hook the viewer.",
  "tool_type": "image_generation",
  "execution_mode": "manual_or_provider",
  "provider_capability": "image_generation",
  "source_artifacts": ["character_reference_images", "creative_plan", "variant_direction", "timeline", "storyboard", "production_package.production_scenes"],
  "required_inputs": [],
  "prompt_to_copy": "Prompt for web/manual generation.",
  "negative_prompt_to_copy": "Negative prompt.",
  "motion_instruction": null,
  "consistency_instruction": null,
  "settings": {"aspect_ratio": "9:16"},
  "expected_outputs": [],
  "review_focus": [],
  "success_criteria": [],
  "status": "ready",
  "output_assets": [],
  "manual_instructions": [],
  "provider_options": [],
  "provider_payload": {},
  "error_message": null
}
```

Allowed step stages:

```text
character_reference, scene_keyframe, video_clip, app_ui_overlay, voiceover, subtitles, assembly, export
```

Allowed tool types:

```text
image_generation, video_generation, image_editing, video_editing, tts, subtitle_generation, final_assembly, export
```

Allowed step statuses:

```text
pending, ready, running, completed, failed, skipped
```

Pipeline endpoints:

```text
GET  /api/projects/{project_id}/variants/{variant_id}/pipeline
POST /api/projects/{project_id}/variants/{variant_id}/pipeline/steps/{step_id}/upload-result
POST /api/projects/{project_id}/variants/{variant_id}/pipeline/steps/{step_id}/run
POST /api/projects/{project_id}/variants/{variant_id}/pipeline/run
```

Upload step result uses multipart form data:

```text
file=<generated image/video>
asset_key=scene_1_keyframe
notes=optional notes
```

Manual and auto render use the same `generation_pipeline.steps`. Manual mode uploads step output assets; auto mode calls configured providers by each step `tool_type`.

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
  - `pipeline_manifest.json`
  - `generation_pipeline.json`
  - `asset_registry.json`
  - `pipeline_prompts.txt`
  - `manual_generation_instructions.txt`
  - `keyframe_prompts.txt`
  - `video_prompts.txt`
  - `ui_overlay_plan.txt`
  - `edit_plan.txt`
  - `script.txt`
  - `storyboard.json`
  - `caption.txt`
  - `generation_pipeline.json`
  - `asset_registry.json`
  - `pipeline_prompts.txt`
  - `manual_generation_instructions.txt`
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

- Runs each variant `generation_pipeline` step-by-step with configured real providers.
- Does not create fake video files.
- Does not create placeholder video files.
- Does not create `mock_video_9x16.txt` or `mock_video_1x1.txt`.

If provider env is missing:

```json
{"detail": "Provider for image_generation is not configured."}
```

If provider env exists but no adapter is implemented:

```json
{"detail": "Provider 'provider-name' is configured but image_generation adapter is not implemented yet."}
```
