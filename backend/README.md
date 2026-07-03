# AI Ads Video Factory Backend MVP

FastAPI backend MVP for creating ad projects, generating a mock product intelligence brief, creative angles, video ad variants, and placeholder video outputs.

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
- Mock outputs: `app/outputs/{project_id}/`

Uploads and outputs are served as static files from:

- `/uploads/...`
- `/outputs/...`

## Main endpoints

- `GET /` - health check
- `POST /api/projects` - create project from multipart form data
- `GET /api/projects` - list projects
- `GET /api/projects/{project_id}` - get project detail
- `POST /api/projects/{project_id}/analyze` - generate Product Intelligence Brief
- `POST /api/projects/{project_id}/angles` - generate 5 creative angles
- `POST /api/projects/{project_id}/generate-variants` - generate ad variants
- `POST /api/projects/{project_id}/mock-render` - create mock video output files and URLs
- `DELETE /api/projects/{project_id}` - delete project and related files

## API contract

Shared BE/FE contract: `../API_CONTRACT.md`

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
curl -X POST http://localhost:8000/api/projects/{project_id}/mock-render
```

The mock render endpoint writes `.json` and `.txt` files in `app/outputs/{project_id}/`. These placeholders are designed to be replaced later by a real video generation provider behind `services/video_provider.py`.
