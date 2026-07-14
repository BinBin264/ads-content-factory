# AI Video Factory Frontend MVP

React + Vite + TypeScript dashboard for the AI Video Factory backend MVP.

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

1. Create a project with product context and a free-form brief. The main UI uses Gemini for prompt planning.
2. Open the project workflow and upload product/app references as a separate step.
3. Generate Plan Creation to turn the brief and uploaded references into timed scene clips.
4. In Automation mode, select a Nano Banana or GPT Image model, then generate the primary character and location references. Manual uploads remain available.
5. Keep or change the image model, then generate or upload one keyframe reference per scene. Every queued job retains the model selected when it was submitted.
6. Review each scene's directorial intent, endpoint, reference roles, prompt QC, voice, overlay, and negative rules.
7. Copy each compact scene prompt into Flow/Kling, or switch to Automation and select a supported ShopAIKey Veo/Grok model for that scene.
8. After a clip is generated or uploaded, record a take verdict. Only accepted footage becomes continuity canon for the next scene.

## API Contract

Shared FE/BE contract: `../API_CONTRACT.md`

The main frontend flow uses `Project` and `PlanCreation`.

Prompt generation and uploaded image understanding use the backend's configured Gemini model exclusively.
