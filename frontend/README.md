# AI Ads Video Factory Frontend MVP

React + Vite + TypeScript dashboard for the AI Ads Video Factory backend MVP.

## Prerequisites

The backend must be running at:

```bash
http://localhost:8000
```

From the backend folder:

```bash
cd ../backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

## Run Frontend

```bash
cd frontend
npm install
npm run dev
```

Open:

```bash
http://127.0.0.1:5173
```

## Available Scripts

- `npm run dev` - start Vite dev server
- `npm run build` - TypeScript build plus Vite production build
- `npm run preview` - preview production build locally

## User Flow

1. Create a project with product context and a free-form brief.
2. Open the project workflow and upload product/app references as a separate step.
3. Generate Plan Creation to turn the brief and uploaded references into one compact scene workflow.
4. Review product locks and uploaded reference mapping.
5. Review scene-by-scene action, camera, voice, overlay, timing, keyframe prompts, final video prompts, and negative rules.
6. Copy keyframe prompts and final video prompts into Kling or another video generation UI for manual testing.

## API Contract

Shared FE/BE contract: `../API_CONTRACT.md`

The main frontend flow uses `Project` and `PlanCreation`.
