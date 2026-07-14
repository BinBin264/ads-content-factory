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
- `qualityStrategy`: take verdicts, attempt budget, and one-variable retake rule.
- `sequenceState`: state/canon revisions, current scene, and take history.

Each scene may include `direction`, `shotContract`, `promptQuality`, and `takeReview`. The final provider prompt is compiled from the current scene contract only; it does not contain the whole project JSON.

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
          "line": "I just found this old coin. What is it?"
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
          "selectedImageUrl": null
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
- `POST /api/projects/{project_id}/reference-assets/{asset_type}/generate` - generate primary character or location reference image when an image provider is configured. `asset_type` is `character` or `location`. The required JSON body is `{ "model": "nano-banana-2" }`; allowed models are `nano-banana`, `nano-banana-2`, `nano-banana-pro`, `gpt-image-1-mini`, `gpt-image-1`, `gpt-image-1.5`, and `gpt-image-2`. Nano Banana uses the Google image endpoint at exact `9:16`; GPT Image uses the OpenAI image endpoint at `1024x1536` with a centered `9:16` safe-crop prompt.
- `POST /api/projects/{project_id}/reference-assets/{asset_type}/generate-async` - enqueue reference generation and return `ImageGenerationJob` immediately. The same required model body is accepted and the job records it as `model_id`.
- `POST /api/projects/{project_id}/scenes/{scene_index}/keyframe-slots/{slot_id}/generate` - generate one keyframe candidate image for a slot with the required image model body. ShopAIKey uploads and supplies only the mapped primary character, primary location, and at most one scene-relevant product/app reference in `image_urls`; unrelated project uploads are excluded.
- `POST /api/projects/{project_id}/scenes/{scene_index}/keyframe-slots/{slot_id}/generate-async` - enqueue keyframe generation with the selected model without blocking generation buttons for other scenes.
- `GET /api/projects/{project_id}/image-generation-jobs` - list image jobs. Use `active_only=true` to return only `queued`, `running`, or `retrying` jobs.
- `GET /api/projects/{project_id}/image-generation-jobs/{job_id}` - poll phase-based `progress`, `phase`, retry attempt, completion, or error state.
- `POST /api/projects/{project_id}/scenes/{scene_index}/keyframe-slots/{slot_id}/select` - select an uploaded/generated image as the keyframe reference for that slot.
- `POST /api/projects/{project_id}/scenes/{scene_index}/video` - submit one real ShopAIKey clip task and return the stored `task_id` immediately. Optional body: `{ "model": "veo3.1-pro" }`. Supported values are `veo3.1-pro`, `veo3.1-fast`, `veo3.1-fast-components`, `grok-video-3`, and `grok-video-3-10s`; omitting the body uses `VIDEO_MODEL_ID`. The backend uploads only the selected keyframe and maps provider fields by model: Veo uses `metadata.aspect_ratio`, while Grok uses `metadata.ratio`, `metadata.duration`, and `metadata.resolution`. `veo3.1-fast-components` is forced to `16:9`; the portrait models use `9:16` for Veo or `2:3` for Grok.
- `GET /api/projects/{project_id}/scenes/{scene_index}/video-status` - poll ShopAIKey once with the stored `task_id`. The project scene stores the provider's real `data.progress` value as `videoProgress`; the frontend calls this endpoint every five seconds until `VIDEO_READY` or `FAILED`.
- `POST /api/projects/{project_id}/scenes/{scene_index}/take-review` - record the operator verdict and observed take state. `keep` and `fix_in_post` update canon and hand the observed end state to the next scene. `edit`, `reroll`, `rewrite`, and `reject` do not update canon.

Example take review:

```json
{
  "verdict": "keep",
  "observed_end_state": {
    "actorPose": "phone in right hand",
    "productState": "coin held in left palm",
    "cameraState": "stable phone close-up"
  },
  "completed_beats": ["Scan the coin"],
  "continuity_breaks": [],
  "accepted_deviations": [],
  "evidence": "Primary product proof is readable and identity is stable.",
  "observation_confidence": "high"
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
