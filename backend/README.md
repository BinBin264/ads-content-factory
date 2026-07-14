# AI Ads Production Factory Backend

FastAPI backend for turning a product brief and uploaded assets into a Plan Creation workflow.

## Run Locally

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Open:

- Health check: `http://localhost:8000/`
- API docs: `http://localhost:8000/docs`

## Storage

- Project data: `app/data/projects.json`
- Uploads: `app/uploads/{project_id}/`

Uploads are served from:

- `/uploads/...`

## Environment

Create `backend/.env`:

```text
GEMINI_API_KEYS=your_first_gemini_api_key,your_second_gemini_api_key
GEMINI_MODEL=gemini-2.5-flash
IMAGE_PROVIDER_NAME=openai-compatible
IMAGE_PROVIDER_API_KEY=your_image_provider_key
IMAGE_PROVIDER_BASE_URL=https://api.openai.com/v1
IMAGE_MODEL_ID=gpt-image-1
VIDEO_PROVIDER_NAME=79ai
VIDEO_PROVIDER_API_KEY=your_79ai_access_token
VIDEO_PROVIDER_BASE_URL=https://api.gommo.net
VIDEO_PROVIDER_DOMAIN=79ai.net
VIDEO_MODEL_ID=veo_omni
VIDEO_MODEL_MODE=flash
VIDEO_MODEL_RATIO=9:16
VIDEO_MODEL_DURATION=4
VIDEO_MODEL_RESOLUTION=720p
VIDEO_TRANSLATE_TO_EN=false
```

`GEMINI_API_KEYS` is required for Plan Creation, scene rewrite, and final prompt regeneration. The backend rotates configured Gemini keys per request and retries the next key on quota, auth, rate-limit, or provider errors. There is no mock fallback.

Image provider env is optional. If it is missing, image generation endpoints fail clearly and do not create placeholder images.

Video provider env is optional. If configured with `VIDEO_PROVIDER_NAME=79ai`, the scene video endpoint uploads selected keyframe images to `POST https://api.gommo.net/ai/image-upload` as `application/x-www-form-urlencoded` with base64 `data`, passes returned image URLs to `POST https://api.gommo.net/ai/create-video` as the JSON-stringified `images` field, creates one `9:16` `4s` `flash` VEO Omni job, polls video status until `download_url` is available, and stores `scene.videoUrl`, `scene.videoJobId`, and provider metadata. If it is missing, video generation fails clearly and does not create mock videos.

## Main Endpoints

- `POST /api/projects` - create project from multipart form data
- `GET /api/projects` - list projects
- `GET /api/projects/{project_id}` - get project detail
- `POST /api/projects/{project_id}/uploads` - upload product/app references after project creation
- `POST /api/projects/{project_id}/plan-creation` - generate the Plan Creation workflow
- `PATCH /api/projects/{project_id}/scenes/{scene_index}` - edit a scene and mark dependent prompts stale
- `POST /api/projects/{project_id}/scenes/{scene_index}/rewrite` - rewrite one scene with Gemini
- `POST /api/projects/{project_id}/scenes/{scene_index}/video-prompt/regenerate` - regenerate one final video prompt
- `POST /api/projects/{project_id}/reference-assets/{asset_type}/generate` - generate primary character/location reference image through configured image provider
- `POST /api/projects/{project_id}/scenes/{scene_index}/keyframe-slots/{slot_id}/generate` - generate one keyframe candidate image through configured image provider
- `POST /api/projects/{project_id}/scenes/{scene_index}/keyframe-slots/{slot_id}/select` - select a keyframe reference image
- `POST /api/projects/{project_id}/scenes/{scene_index}/video` - generate/poll one 4s 9:16 VEO Omni clip through the configured 79AI provider; no mock output
- `DELETE /api/projects/{project_id}` - delete project and uploaded files

Main endpoint flow:

```text
POST /api/projects
POST /api/projects/{project_id}/uploads
POST /api/projects/{project_id}/plan-creation
GET  /api/projects/{project_id}
```

## Plan Creation

The endpoint stores output in `project.creative_plan` and returns the same object. It includes:

- `productAnalysis`
- `productReferences`
- `primaryCharacter`
- `primaryLocation`
- `scenes`

Each scene is normalized to a 4-second clip. It includes action, product moment, camera, voice lines, overlay text, timing beats, keyframe prompt slots, final video prompt, negative rules, stale flags, selected keyframe reference state, and provider status fields.

Video generation does not create fake output. If no provider is configured, the scene video endpoint returns:

```text
Video provider is not configured. Set VIDEO_PROVIDER_NAME and VIDEO_PROVIDER_API_KEY.
```

## Example Flow

```bash
curl -X POST http://localhost:8000/api/projects \
  -F "product_name=Coin Scanner App" \
  -F "product_category=Mobile app" \
  -F "product_description=An app that helps users scan old coins, identify coin details, and view estimated reference value." \
  -F "brief=Create a 20s vertical UGC ad for people who find old coins at home. Show the scan flow from uploaded screenshots and avoid guaranteed appraisal claims."
```

Then call:

```bash
curl -X POST http://localhost:8000/api/projects/{project_id}/uploads \
  -F "files=@app_scan.png" \
  -F "files=@app_result.png"

curl -X POST http://localhost:8000/api/projects/{project_id}/plan-creation
```
