# API Contract

Shared project shape for backend and frontend integration.

Main flow:

```text
Brief Input
-> Plan Creation
-> Manual video testing
```

Endpoint flow:

```text
POST /api/projects
POST /api/projects/{project_id}/uploads
POST /api/projects/{project_id}/plan-creation
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

Uploading new references clears `project.creative_plan` and `project.vision_analysis`, because the next Plan Creation should be regenerated against the new asset set.

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
  "scenes": [
    {
      "sceneIndex": 1,
      "narrativePurpose": "hook + product_app_introduction",
      "title": "Found coin scan",
      "durationSec": 10,
      "sceneGoal": "Show why the user needs the app and start the scan.",
      "visualAction": "Actor finds an old coin, opens the app, and starts scanning.",
      "productMoment": "Phone screen uses the uploaded scan reference.",
      "characterAction": "Primary actor reacts with curiosity and scans the coin.",
      "locationUse": "Warm tabletop setting with the coin and phone visible.",
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
          "productReferenceIds": ["file_001"]
        }
      ],
      "finalVideoPrompt": "Generate a 10-second vertical UGC video using the uploaded app screen as a visual ingredient...",
      "negativeRules": ["do not redesign the product/app", "no unreadable UI text"]
    }
  ]
}
```

## Current Scope

The active contract ends at Plan Creation. Video provider automation can be added later on top of the same scene schema.
