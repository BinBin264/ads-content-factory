# AI Ads Video Factory Backend MVP

FastAPI backend MVP for creating ad projects, generating product intelligence, creative angles, video ad variants, and provider-based video outputs.

## Run locally

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
- Outputs: `app/outputs/{project_id}/`

Uploads and outputs are served as static files from:

- `/uploads/...`
- `/outputs/...`

## Main endpoints

- `GET /` - health check
- `POST /api/projects` - create project from multipart form data
- `GET /api/projects` - list projects
- `GET /api/projects/{project_id}` - get project detail
- `POST /api/projects/{project_id}/analyze` - generate Product Intelligence, Product Brief, and Vision Analysis
- `POST /api/projects/{project_id}/angles` - generate 5 creative angles
- `POST /api/projects/{project_id}/generate-variants` - generate ad variants
- `POST /api/projects/{project_id}/render` - render video through configured video provider
- `DELETE /api/projects/{project_id}` - delete project and related files

## API contract

Shared BE/FE contract: `../API_CONTRACT.md`

## LLM prompt templates

Reusable prompt templates for future real providers live in `app/prompts/`:

- `product_intelligence_agent.md`
- `creative_angle_agent.md`
- `script_storyboard_agent.md`
- `video_prompt_optimizer_agent.md`
- `demo_coin_scanner.md`

These files define the LLM contract used by Gemini-backed agents.

## Product Intelligence Layer

The analyze flow calls:

1. `GeminiVisionProvider`
2. `ProductIntelligenceService` with Gemini when `GEMINI_API_KEYS` or `GEMINI_API_KEY` is configured
3. `PlaybookEngine`
4. compatibility mapper to `ProductBrief`

Supported product types: `mobile_app`, `skincare`, `fnb`, `ecommerce`, `education`, and `general`.

## Gemini API

Create `backend/.env` from `.env.example`:

```text
GEMINI_API_KEYS=your_first_gemini_api_key,your_second_gemini_api_key
GEMINI_MODEL=gemini-2.5-flash
```

`GEMINI_API_KEY=your_gemini_api_key_here` is still supported for one-key local setups. When `GEMINI_API_KEYS` contains multiple comma-separated keys, the backend rotates keys per request and retries the next key on Gemini quota, rate-limit, auth, or provider errors.

Gemini is required for Vision Analysis, Product Intelligence, Creative Angles, and Script + Storyboard. If all Gemini keys are missing or the API response cannot be validated, the backend returns an API error.

## Example flow

Create a project:

```bash
curl -X POST http://localhost:8000/api/projects \
  -F "product_name=FocusFlow" \
  -F "product_category=mobile app" \
  -F "product_description=A productivity app that turns messy tasks into a daily action plan" \
  -F "audience=busy founders and operators" \
  -F "goal=app_install" \
  -F "platform=tiktok" \
  -F "duration=20s" \
  -F "tone=UGC, natural, realistic"
```

Then call the generation endpoints with the returned `project_id`:

```bash
curl -X POST http://localhost:8000/api/projects/{project_id}/analyze
curl -X POST http://localhost:8000/api/projects/{project_id}/angles
curl -X POST http://localhost:8000/api/projects/{project_id}/generate-variants \
  -H "Content-Type: application/json" \
  -d "{\"variant_count\":2}"
curl -X POST http://localhost:8000/api/projects/{project_id}/render
```

The render endpoint requires a production adapter behind `services/video_provider.py`.
