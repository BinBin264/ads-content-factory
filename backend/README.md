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
```

`GEMINI_API_KEYS` is required for Plan Creation. The backend rotates configured Gemini keys per request and retries the next key on quota, auth, rate-limit, or provider errors. There is no mock fallback.

## Main Endpoints

- `POST /api/projects` - create project from multipart form data
- `GET /api/projects` - list projects
- `GET /api/projects/{project_id}` - get project detail
- `POST /api/projects/{project_id}/uploads` - upload product/app references after project creation
- `POST /api/projects/{project_id}/plan-creation` - generate the Plan Creation workflow
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
- `scenes`

Each scene includes action, product moment, camera, voice lines, overlay text, timing beats, keyframe prompts, final video prompt, and negative rules.

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
