# API Contract

Shared project shape for backend and frontend integration.

Main flow:

```text
Brief Input
-> Plan Creation
-> Product/character/location references
-> timed scene clips
-> Manual video testing
```

Endpoint flow:

```text
POST /api/projects
POST /api/projects/{project_id}/uploads
POST /api/projects/{project_id}/plan-creation
PATCH /api/projects/{project_id}/scenes/{scene_index}
POST  /api/projects/{project_id}/scenes/{scene_index}/video-prompt/regenerate
POST  /api/projects/{project_id}/scenes/{scene_index}/keyframe-slots/{slot_id}/select
POST  /api/projects/{project_id}/scenes/{scene_index}/video
GET   /api/projects/{project_id}/scenes/{scene_index}/video-status
POST  /api/projects/{project_id}/scenes/{scene_index}/take-review
GET  /api/projects/{project_id}
```

## Project Shape

```json
{
  "id": "project_001",
  "product_name": "Coin Scanner App",
  "product_category": "mobile app",
  "product_description": "An app that scans old coins and shows coin details and estimated reference value.",
  "brief": "Create a 20s vertical UGC ad for people who find old coins at home.",
  "audience": null,
  "goal": "app_install",
  "platform": "tiktok",
  "duration": "20s",
  "tone": "UGC, natural, realistic",
  "cta": null,
  "claims_to_avoid": [],
  "brand_colors": [],
  "uploaded_files": [],
  "vision_analysis": null,
  "creative_plan": null,
  "created_at": "2026-07-02T00:00:00Z",
  "updated_at": "2026-07-02T00:00:00Z"
}
```

For `POST /api/projects`, the frontend sends multipart form data:

```text
product_name=Coin Scanner App
product_category=Mobile app
product_description=An app that scans old coins.
brief=Create a short vertical UGC ad...
```

The main frontend form does not upload files during project creation. Uploaded references are a separate workflow step.

The backend uses `GEMINI_MODEL` and the rotating `GEMINI_API_KEYS` pool for all planning and prompt generation. Provider/model selection is not accepted per project.

## Upload References Endpoint

```text
POST /api/projects/{project_id}/uploads
```

Multipart form data:

```text
files=<product image>
files=<app screenshot>
files=<logo or moodboard>
```

Response: `Project`

Uploading new references appends to `project.uploaded_files`. It does not clear `creative_plan`, because the same endpoint is also used after Plan Creation to attach generated keyframes or Flow references. Regenerate Plan Creation manually when uploaded product references should change the plan.

Compatibility fields such as `audience`, `goal`, `platform`, `duration`, `tone`, `cta`, `claims_to_avoid`, and `brand_colors` may still exist on `Project`, but they are not required in the main frontend form.

## UploadedFileInfo

```json
{
  "id": "file_001",
  "file_name": "app_scan.png",
  "content_type": "image/png",
  "size_bytes": 102400,
  "path": "backend/app/uploads/project_001/01_app_scan.png",
  "url": "/uploads/project_001/01_app_scan.png"
}
```

## VisionAnalysis

```json
{
  "detected_objects": ["phone", "coin"],
  "detected_product_type": "mobile_app",
  "detected_visual_style": "natural UGC",
  "detected_brand_colors": [],
  "detected_ui_elements": ["scan button", "result card"],
  "detected_text": [],
  "confidence": 0.8,
  "notes": []
}
```

## Plan Creation Endpoint

```text
POST /api/projects/{project_id}/plan-creation
```

Response: `PlanCreation`

The backend also stores the response in `project.creative_plan`.

In addition to product/reference/scene fields, `PlanCreation` now includes:

- `storySpine`: global story objective, opening condition, and final outcome.
- `worldBible`: canonical character, location, product, visual, lighting, atmosphere, and anti-drift locks.
- `surfaceProfile`: conservative Google Veo generation constraints.
- `safetyPlan`: unsupported-claim and authorized-reference rules.
- `qualityStrategy`: `Accept Clip` / `Regenerate Clip` behavior and the clip attempt budget.
- `sequenceState`: workflow revision, current scene, and clip acceptance history.

Each scene may include `openingState`, `direction`, `shotContract`, `promptQuality`, and `takeReview`. `openingState` is the frozen frame-0 state before scene motion begins. The selected keyframe carries static visual state; the final provider prompt contains only the current motion/audio delta and does not contain the whole project JSON.

`voiceLines[].generationMode` is either `native` or `post_voiceover`. The planner keeps at most one short line within the native speech budget; longer or multi-line narration is preserved for post-production so adjacent clips do not repeat or overlap dialogue.

## PlanCreation Shape

```json
{
  "productAnalysis": {
    "productType": "mobile app",
    "visibleElements": ["coin scan screen", "coin detail result screen"],
    "coreBenefit": "Scan an old coin and view useful identification details plus estimated reference value.",
    "brandOrVisualCues": ["yellow app UI", "phone camera scan flow"],
    "doNotAssume": ["guaranteed value", "100% accurate appraisal"],
    "productLockPrompt": "Preserve the app scan flow and result/detail screen from uploaded references."
  },
  "productReferences": [
    {
      "id": "file_001",
      "name": "Coin scan screen",
      "kind": "app_screen",
      "visualDescription": "Phone screenshot showing a coin scan interface.",
      "lockPrompt": "Keep the same app layout and visible scan UI.",
      "useWhen": "Use for scanning or phone close-up moments.",
      "isPrimary": true
    }
  ],
  "primaryCharacter": {
    "name": "Primary actor",
    "description": "single consistent actor description suitable for ads",
    "imagePrompt": "prompt to generate one clean reference image of this actor",
    "consistencyPrompt": "identity lock text for later keyframes",
    "status": "pending",
    "imageUrl": null,
    "candidateImages": []
  },
  "primaryLocation": {
    "name": "Primary setting",
    "description": "single consistent environment description with cinematic mood and recurring props",
    "imagePrompt": "prompt to generate one clean location reference image",
    "consistencyPrompt": "location lock text for later keyframes",
    "status": "pending",
    "imageUrl": null,
    "candidateImages": []
  },
  "scenes": [
    {
      "sceneIndex": 1,
      "narrativePurpose": "hook + product_app_introduction",
      "title": "Found coin scan",
      "durationSec": 6,
      "sceneGoal": "Show why the user needs the app.",
      "openingState": "The actor's empty hand rests beside the coin before reaching for it.",
      "visualAction": "Actor finds an old coin and reacts with curiosity.",
      "productMoment": "Coin and phone are visible as the product need is established.",
      "characterAction": "Primary actor reacts with curiosity.",
      "locationUse": "Primary location tabletop setting with the coin and phone visible.",
      "camera": {
        "selected": "eye-level medium shot",
        "shot": "medium shot to phone close-up",
        "movement": "gentle push-in",
        "composition": "coin and phone readable at scan moment",
        "alternatives": ["over-the-shoulder phone close-up"]
      },
      "voiceLines": [
        {
          "speaker": "Primary actor",
          "timing": "0-6s",
          "actionState": "holding the old coin",
          "emotion": "curious",
          "delivery": "natural UGC",
          "line": "I just found this old coin. What is it?",
          "generationMode": "post_voiceover"
        }
      ],
      "ambientAudio": "soft room tone and coin handling sounds",
      "onScreenText": "Scan old coins",
      "timingBeats": ["0-3s: find coin", "4-10s: scan coin"],
      "keyframePrompts": [
        {
          "id": "kf_setup",
          "label": "Actor and product setup",
          "timing": "0-3s",
          "purpose": "Establish actor, coin, phone, table, and camera.",
          "prompt": "Realistic UGC vertical frame of an actor holding an old coin beside a smartphone app scan screen.",
          "productReferenceIds": ["file_001"],
          "stale": false,
          "candidates": [],
          "selectedCandidateId": null,
          "selectedImageUrl": null,
          "qualityGate": {
            "status": "awaiting_image",
            "acceptedCandidateId": null,
            "defects": [],
            "checks": ["exactly one primary actor is visible", "hands and prop ownership are valid"],
            "repairRule": "Reject or reroll a structurally bad keyframe; do not ask the video model to repair it."
          }
        }
      ],
      "finalVideoPrompt": "Scene video prompt using the selected keyframe as the visual anchor. Duration, aspect ratio, and model mode are provider parameters, not prompt text.",
      "negativeRules": ["do not redesign the product/app", "no unreadable UI text"],
      "keyframePromptStale": false,
      "finalVideoPromptStale": false,
      "status": "DRAFT",
      "videoUrl": null,
      "videoError": null,
      "videoProvider": null,
      "videoModel": null,
      "videoJobId": null,
      "videoRatio": null,
      "videoDuration": null,
      "videoMode": null,
      "videoResolution": null,
      "videoProgress": null,
      "videoReferenceUploads": [],
      "videoStatusPayload": null
    }
  ]
}
```

## Production Workflow Endpoints

- `PATCH /api/projects/{project_id}/product-references/{reference_id}` - update product reference metadata.
- `PATCH /api/projects/{project_id}/scenes/{scene_index}` - edit scene fields and mark keyframe/final prompts stale.
- `POST /api/projects/{project_id}/scenes/{scene_index}/rewrite` - rewrite a scene with the configured Gemini model.
- `PATCH /api/projects/{project_id}/scenes/{scene_index}/video-prompt` - manually update final video prompt.
- `POST /api/projects/{project_id}/scenes/{scene_index}/video-prompt/regenerate` - regenerate final video prompt with the configured Gemini model.
- `PATCH /api/projects/{project_id}/scenes/{scene_index}/keyframe-slots/{slot_id}` - edit a keyframe prompt slot.
- `POST /api/projects/{project_id}/reference-assets/{asset_type}/generate` - generate primary character or location reference image when an image provider is configured. `asset_type` is `character` or `location`. The required JSON body is `{ "model": "nano-banana-2" }`; allowed models are `nano-banana`, `nano-banana-2`, `nano-banana-pro`, `gpt-image-1`, `gpt-image-1.5`, `gpt-image-2`, and `gpt-image-2-all`. Nano Banana uses the Google image endpoint at exact `9:16`; GPT Image uses the OpenAI image endpoint at `1024x1536` with a centered `9:16` safe-crop prompt.
- `POST /api/projects/{project_id}/reference-assets/{asset_type}/generate-async` - enqueue reference generation and return `ImageGenerationJob` immediately. The same required model body is accepted and the job records it as `model_id`.
- `POST /api/projects/{project_id}/scenes/{scene_index}/keyframe-slots/{slot_id}/generate` - generate one keyframe candidate image for a slot with the required image model body. ShopAIKey uploads and supplies only the mapped primary character, primary location, and at most one scene-relevant product/app reference in `image_urls`; unrelated project uploads are excluded.
- `POST /api/projects/{project_id}/scenes/{scene_index}/keyframe-slots/{slot_id}/generate-async` - enqueue keyframe generation with the selected model without blocking generation buttons for other scenes.
- `GET /api/projects/{project_id}/image-generation-jobs` - list image jobs. Use `active_only=true` to return only `queued`, `running`, or `retrying` jobs.
- `GET /api/projects/{project_id}/image-generation-jobs/{job_id}` - poll phase-based `progress`, `phase`, retry attempt, completion, or error state.
- `POST /api/projects/{project_id}/scenes/{scene_index}/keyframe-slots/{slot_id}/select` - select an uploaded/generated image as the keyframe reference for that slot.
- `POST /api/projects/{project_id}/scenes/{scene_index}/keyframe-slots/{slot_id}/review` - accept or reject the currently selected keyframe. Body: `{ "verdict": "accept" }` or `{ "verdict": "reject", "defects": ["duplicate_actor", "bad_hands"], "notes": "optional operator note" }`. Acceptance is tied to `selectedCandidateId` and locks prompt edits, generation, candidate selection, and upload replacement. Reject the keyframe first to unlock those actions.
- `POST /api/projects/{project_id}/scenes/{scene_index}/video` - submit one real ShopAIKey clip task and return the stored `task_id` immediately. The selected Phase 2 keyframe must first pass the keyframe review endpoint with `verdict=accept`; clips do not depend on review state from previous scenes. Optional body: `{ "model": "veo3.1-pro", "force": false }`. Set `force=true` to discard the current clip task/output and generate a replacement without changing its keyframe or any later scene. Supported model values are `veo3.1-pro`, `veo3.1-fast`, `grok-video-3`, and `grok-video-3-10s`; omitting `model` uses `VIDEO_MODEL_ID`. The backend uploads only the selected keyframe and maps provider fields by model: Veo uses `metadata.aspect_ratio`, while Grok uses `metadata.ratio`, `metadata.duration`, and `metadata.resolution`. The portrait models use `9:16` for Veo or `2:3` for Grok.
- `POST /api/projects/{project_id}/scenes/{scene_index}/video/regenerate` - always discard the current scene clip/task state and submit a replacement with the selected model. The main frontend uses this dedicated endpoint for `Regenerate Clip` so replacement cannot fall through to the idempotent existing-video response.
- `GET /api/projects/{project_id}/scenes/{scene_index}/video-status` - poll ShopAIKey once with the stored `task_id`. The project scene stores the provider's real `data.progress` value as `videoProgress`; the frontend calls this endpoint every five seconds until `VIDEO_READY` or `FAILED`.
- `POST /api/projects/{project_id}/scenes/{scene_index}/take-review` - accept the current generated/uploaded clip. The body is `{ "verdict": "keep" }`. Acceptance marks only the current clip complete; it does not collect an observed end state, recompile later prompts, alter Phase 2 keyframes, or gate generation of other clips.

Example take review:

```json
{
  "verdict": "keep"
}
```

If video provider env is missing, this endpoint returns:

```text
Video provider is not configured. Set IMAGE_PROVIDER_API_KEY or VIDEO_PROVIDER_API_KEY for ShopAIKey.
```

If image provider env is missing, image generation endpoints return:

```text
Image provider is not configured. Set IMAGE_PROVIDER_NAME and IMAGE_PROVIDER_API_KEY.
```

Current scope has no fake videos and no mock provider output.
