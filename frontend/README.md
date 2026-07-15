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
5. Keep or change the image model, then generate or upload one opening keyframe reference per scene. Every queued job retains the model selected when it was submitted.
6. Accept or reject each keyframe after checking duplicate actors, hands, handedness, prop ownership, and product/UI fidelity. An accepted keyframe locks its prompt and replacement actions; reject it first to edit or regenerate. Clip automation stays locked until the current selected keyframe is accepted.
7. Review each scene's final video prompt, voice/subtitle plan, and overlay text.
8. Generate any scene whose keyframe has been accepted. Copy its prompt into Flow/Kling, or switch to Automation and select a supported ShopAIKey Veo/Grok model.
9. In Manual mode, upload or replace one clip per scene; no clip review action is required. In Automation mode, choose `Accept Clip` to mark a generated clip complete or `Regenerate Clip` to replace it. Review actions do not alter later keyframes or prompts.

## API Contract

Shared FE/BE contract: `../API_CONTRACT.md`

The main frontend flow uses `Project` and `PlanCreation`.

Prompt generation and uploaded image understanding use the backend's configured Gemini model exclusively.
