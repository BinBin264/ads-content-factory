# AI Ads Production Factory Backend

FastAPI backend for turning a product brief and uploaded assets into a Creative Plan, two video variants, production prompts, package exports, and real video-provider rendering.

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
- Exported production packages: `app/outputs/{project_id}/{variant_id}/`

Uploads and outputs are served from:

- `/uploads/...`
- `/outputs/...`

## Environment

Create `backend/.env`:

```text
GEMINI_API_KEYS=your_first_gemini_api_key,your_second_gemini_api_key
GEMINI_MODEL=gemini-2.5-flash
VIDEO_PROVIDER_NAME=your_provider_name
VIDEO_PROVIDER_API_KEY=your_video_provider_key
```

`GEMINI_API_KEYS` is required for Creative Plan, Script + Storyboard, Character Planner, Reference Prompts, and Production Scenes. The backend rotates configured Gemini keys per request and retries the next key on quota, auth, rate-limit, or provider errors.

Render Video requires `VIDEO_PROVIDER_NAME` and `VIDEO_PROVIDER_API_KEY`. If the provider env is missing, `/render` returns:

```json
{"detail": "Video provider is not configured. Set VIDEO_PROVIDER_NAME and VIDEO_PROVIDER_API_KEY."}
```

If provider env exists but no adapter is implemented, `/render` returns:

```json
{"detail": "Provider is configured but render adapter is not implemented yet."}
```

## Main Endpoints

- `POST /api/projects` - create project from multipart form data
- `GET /api/projects` - list projects
- `GET /api/projects/{project_id}` - get project detail
- `POST /api/projects/{project_id}/creative-plan` - generate the compact Creative Plan and two variant directions
- `POST /api/projects/{project_id}/generate-variants` - generate exactly two variants from `project.creative_plan`
- `POST /api/projects/{project_id}/export-production-package` - export package files and zip
- `POST /api/projects/{project_id}/render` - call a real configured video provider
- `DELETE /api/projects/{project_id}` - delete project and related files

Legacy endpoints:

- `POST /api/projects/{project_id}/analyze` - legacy compatibility response with Creative Plan plus old compatibility fields
- `POST /api/projects/{project_id}/angles` - deprecated legacy endpoint

Main endpoint flow:

```text
POST /api/projects
POST /api/projects/{project_id}/creative-plan
POST /api/projects/{project_id}/generate-variants
POST /api/projects/{project_id}/export-production-package
POST /api/projects/{project_id}/render
```

## Production Package

Each generated variant keeps the legacy fields (`script`, `storyboard`, `caption`, `title`) and adds:

- `production_package.character_plan`
- `production_package.character_bible`
- `production_package.character_reference_prompts`
- `production_package.production_scenes`
- `production_package.edit_plan`
- `production_package.app_ui_overlay_notes`
- `production_package.asset_checklist`
- `production_package.compliance_notes`
- `production_package.render_sequence`

Export Production Package writes:

```text
/project_output
  creative_plan.json
  variant_A.json
  variant_B.json

  /variant_A
    script.txt
    storyboard.json
    video_prompts.txt
    keyframe_prompts.txt
    voiceover.txt
    subtitles.srt
    cover_prompt.txt
    caption.txt
    edit_plan.txt

  /variant_B
    script.txt
    storyboard.json
    video_prompts.txt
    keyframe_prompts.txt
    voiceover.txt
    subtitles.srt
    cover_prompt.txt
    caption.txt
    edit_plan.txt
```

Each variant folder under `app/outputs/{project_id}/{variant_id}/` also includes production package files such as `character_bible.json`, `character_reference_prompts.txt`, `production_scenes.json`, `ui_overlay_plan.txt`, `generation_pipeline.json`, and `production_package.zip`.

## Example Flow

```bash
curl -X POST http://localhost:8000/api/projects \
  -F "product_name=Coin Scanner App" \
  -F "product_category=Mobile app" \
  -F "product_description=An app that helps users scan old coins, identify coin details, and view estimated reference value." \
  -F "audience=People who find old coins at home, casual coin collectors, adults with coin jars." \
  -F "goal=app_install" \
  -F "platform=tiktok" \
  -F "duration=20s" \
  -F "tone=Natural UGC, relatable, curiosity-driven, realistic, not too polished." \
  -F "cta=Download now and scan your old coins." \
  -F "claims_to_avoid=Guaranteed value" \
  -F "claims_to_avoid=100% accurate appraisal" \
  -F "claims_to_avoid=you will make money"
```

Then call:

```bash
curl -X POST http://localhost:8000/api/projects/{project_id}/creative-plan
curl -X POST http://localhost:8000/api/projects/{project_id}/generate-variants \
  -H "Content-Type: application/json" \
  -d "{\"variant_count\":2}"
curl -X POST http://localhost:8000/api/projects/{project_id}/export-production-package
curl -X POST http://localhost:8000/api/projects/{project_id}/render
```
