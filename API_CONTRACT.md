# API Contract

Shared project shape for backend and frontend integration.

Main flow:

```text
Brief Input
-> Plan Creation
-> Product/character/location references
-> 4-second scene clips
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
      "durationSec": 4,
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
          "timing": "0-4s",
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
      "finalVideoPrompt": "Create a 4-second vertical video using selected reference images as visual ingredients...",
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
      "videoReferenceUploads": [],
      "videoStatusPayload": null
    }
  ]
}
```

## Production Workflow Endpoints

- `PATCH /api/projects/{project_id}/product-references/{reference_id}` - update product reference metadata.
- `PATCH /api/projects/{project_id}/scenes/{scene_index}` - edit scene fields and mark keyframe/final prompts stale.
- `POST /api/projects/{project_id}/scenes/{scene_index}/rewrite` - rewrite a scene with Gemini.
- `PATCH /api/projects/{project_id}/scenes/{scene_index}/video-prompt` - manually update final video prompt.
- `POST /api/projects/{project_id}/scenes/{scene_index}/video-prompt/regenerate` - regenerate final video prompt with Gemini.
- `PATCH /api/projects/{project_id}/scenes/{scene_index}/keyframe-slots/{slot_id}` - edit a keyframe prompt slot.
- `POST /api/projects/{project_id}/reference-assets/{asset_type}/generate` - generate primary character or location reference image when an image provider is configured. `asset_type` is `character` or `location`.
- `POST /api/projects/{project_id}/scenes/{scene_index}/keyframe-slots/{slot_id}/generate` - generate one keyframe candidate image for a slot when an image provider is configured.
- `POST /api/projects/{project_id}/scenes/{scene_index}/keyframe-slots/{slot_id}/select` - select an uploaded/generated image as the keyframe reference for that slot.
- `POST /api/projects/{project_id}/scenes/{scene_index}/video` - generate or poll one real 4-second scene clip. With `VIDEO_PROVIDER_NAME=79ai`, backend first uploads selected keyframe images to `POST https://api.gommo.net/ai/image-upload` as `application/x-www-form-urlencoded` with base64 `data`, sends `POST https://api.gommo.net/ai/create-video` as `application/x-www-form-urlencoded`, passes returned image URLs in `images` as a JSON-stringified URL array, calls `veo_omni` in `flash` mode, ratio `9:16`, duration `4`, then polls video status until `download_url` is available. The scene stores `videoUrl`, `videoJobId`, provider metadata, and uploaded image URLs.

If video provider env is missing, this endpoint returns:

```text
Video provider is not configured. Set VIDEO_PROVIDER_NAME and VIDEO_PROVIDER_API_KEY.
```

If image provider env is missing, image generation endpoints return:

```text
Image provider is not configured. Set IMAGE_PROVIDER_NAME and IMAGE_PROVIDER_API_KEY.
```

Current scope has no fake videos and no mock provider output.
