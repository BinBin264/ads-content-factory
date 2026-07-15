# AI Video Factory Backend

FastAPI backend for turning a video ad brief or content idea and uploaded assets into a Plan Creation workflow.

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
GEMINI_REQUEST_TIMEOUT_SECONDS=180
GEMINI_TRANSIENT_MAX_ATTEMPTS=2
GEMINI_RETRY_BASE_SECONDS=1.5
IMAGE_PROVIDER_NAME=shopaikey-google
IMAGE_PROVIDER_API_KEY=your_image_provider_key
IMAGE_PROVIDER_BASE_URL=https://api.shopaikey.com
IMAGE_OUTPUT_SIZE=2K
IMAGE_GENERATION_CONCURRENCY=2
IMAGE_GENERATION_MAX_RETRIES=3
IMAGE_GENERATION_RETRY_BASE_SECONDS=2
VIDEO_PROVIDER_NAME=shopaikey
# Optional when IMAGE_PROVIDER_API_KEY is the same ShopAIKey credential.
VIDEO_PROVIDER_API_KEY=your_optional_dedicated_shopaikey_key
VIDEO_PROVIDER_BASE_URL=https://api.shopaikey.com
VIDEO_MODEL_ID=veo3.1-pro
VIDEO_MODEL_RATIO=9:16
VIDEO_ENHANCE_PROMPT=false
VIDEO_ENABLE_UPSAMPLE=true
VIDEO_REFERENCE_LIMIT=1
VIDEO_REQUEST_TIMEOUT_SECONDS=90
```

`VIDEO_MODEL_ID` is the default for requests without a model. The Phase 3 selector can override it with `veo3.1-pro`, `veo3.1-fast`, `grok-video-3`, or `grok-video-3-10s`.

Automation mode must select `nano-banana`, `nano-banana-2`, `nano-banana-pro`, `gpt-image-1`, `gpt-image-1.5`, `gpt-image-2`, or `gpt-image-2-all` for each character, location, or keyframe job. There is no env model fallback. The selected model is captured by the queued job, so changing the selector does not alter jobs already running. Nano Banana requests use `/images/google/generations` and preserve the requested `9:16` canvas. GPT Image requests use `/images/openai/generations`, upload up to four mapped references through `image_urls`, and generate on the supported `1024x1536` portrait canvas with a centered `9:16` safe-crop instruction.

Plan Creation, uploaded image understanding, scene rewrites, and final prompt regeneration use Gemini exclusively. `GEMINI_MODEL` selects the model and `GEMINI_API_KEYS` supplies the rotating key pool.

There is no mock fallback.

Image provider env is optional and independent from Gemini planning. With `IMAGE_PROVIDER_NAME=shopaikey-google`, reference generation calls `POST /images/google/generations`. Storyboard keyframes upload only the minimum routed references through `POST /upload/images`: product/UI close-ups use one product reference; actor-plus-product shots use product plus character; actor-only shots use character plus location. Uploaded URLs are cached per file while the backend process is running. Async image endpoints return a job immediately, expose phase-based percentage progress, run up to `IMAGE_GENERATION_CONCURRENCY` jobs at once, queue overflow, and retry temporary `429`, `503`, timeout, and `524` failures serially with exponential backoff. `IMAGE_GENERATION_MAX_RETRIES=3` means three retries after the initial request. Set its credential only through `IMAGE_PROVIDER_API_KEY`. If configuration is missing, generation fails clearly and does not create placeholder images.

Video automation uses ShopAIKey only. The scene endpoint uploads the selected keyframe to `POST /upload/images`, sends its URL as the single item in `metadata.images` to `POST /v1/video/generations`, and polls `GET /v1/video/generations/{task_id}` until `SUCCESS` exposes `result_url`. The default model is `veo3.1-pro` in `9:16` first-frame mode, prompt enhancement is disabled to preserve the compiled production prompt, and provider upsampling is enabled. ShopAIKey's public Veo contract does not expose a duration parameter, so `scene.durationSec` remains the editorial target rather than a submitted API field. Missing configuration fails clearly and never creates mock video.

## Main Endpoints

- `POST /api/projects` - create project from multipart form data
- `GET /api/projects` - list projects
- `GET /api/projects/{project_id}` - get project detail
- `POST /api/projects/{project_id}/uploads` - upload product/app references after project creation
- `POST /api/projects/{project_id}/plan-creation` - generate the Plan Creation workflow
- `PATCH /api/projects/{project_id}/scenes/{scene_index}` - edit a scene and mark dependent prompts stale
- `POST /api/projects/{project_id}/scenes/{scene_index}/rewrite` - rewrite one scene with the configured Gemini model
- `POST /api/projects/{project_id}/scenes/{scene_index}/video-prompt/regenerate` - regenerate one final video prompt
- `POST /api/projects/{project_id}/reference-assets/{asset_type}/generate` - generate primary character/location reference image; accepts optional `{ "model": "nano-banana-2" }`
- `POST /api/projects/{project_id}/reference-assets/{asset_type}/generate-async` - enqueue character/location generation with the selected image model and return an image job
- `POST /api/projects/{project_id}/scenes/{scene_index}/keyframe-slots/{slot_id}/generate` - generate one keyframe candidate with an optional image model request
- `POST /api/projects/{project_id}/scenes/{scene_index}/keyframe-slots/{slot_id}/generate-async` - enqueue one keyframe and retain its selected image model without blocking other scene buttons
- `GET /api/projects/{project_id}/image-generation-jobs` - list queued/running/completed image jobs and progress
- `GET /api/projects/{project_id}/image-generation-jobs/{job_id}` - poll one image job
- `POST /api/projects/{project_id}/scenes/{scene_index}/keyframe-slots/{slot_id}/select` - select a keyframe reference image
- `POST /api/projects/{project_id}/scenes/{scene_index}/keyframe-slots/{slot_id}/review` - accept or reject the selected keyframe; automated video generation requires acceptance tied to the current candidate, and acceptance locks prompt/image replacement until rejection
- `POST /api/projects/{project_id}/scenes/{scene_index}/video` - submit one real ShopAIKey Veo or Grok clip from the accepted Phase 2 keyframe; optional fields are `model` and `force`; `force=true` replaces only the current clip; no mock output
- `POST /api/projects/{project_id}/scenes/{scene_index}/video/regenerate` - dedicated replacement endpoint used by `Regenerate Clip`; always clears the current scene clip/task before submitting the selected model
- `GET /api/projects/{project_id}/scenes/{scene_index}/video-status` - poll one ShopAIKey task and store the provider's real `progress` percentage
- `POST /api/projects/{project_id}/scenes/{scene_index}/take-review` - accept a generated/uploaded clip with `{ "verdict": "keep" }`; acceptance marks only that clip complete and does not rewrite later keyframes or prompts
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
- `storySpine`
- `worldBible`
- `surfaceProfile`
- `safetyPlan`
- `qualityStrategy`
- `sequenceState`

Each scene has a `durationSec` selected from `4`, `6`, `8`, or `10` based on action complexity. It includes an opening state, one motion delta, product moment, camera, native/post voice lines, overlay text, timing beats, one keyframe prompt slot with a review gate, final video prompt, negative rules, stale flags, selected keyframe reference state, provider status fields, directorial intent, a shot contract, prompt QC, and optional take review.

`ProductionOrchestrator` treats the structured plan as source of truth and compiles a compact natural-language prompt for only the current Veo scene. Canonical character/location/product references are separated from clip approval state. Reference bindings declare what each image transfers and what it must ignore. Phase 2 keyframes remain fixed while Phase 3 clips are accepted or regenerated independently.

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
