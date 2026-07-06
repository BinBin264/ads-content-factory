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

## Run frontend

```bash
cd frontend
npm install
npm run dev
```

Open:

```bash
http://127.0.0.1:5173
```

## Available scripts

- `npm run dev` - start Vite dev server
- `npm run build` - TypeScript build plus Vite production build
- `npm run preview` - preview production build locally

## User flow

1. Create a project with product details, brand inputs, and optional uploads.
2. Generate Creative Plan to normalize the brief into one compact production strategy.
3. Review the two default Variant Directions:
   - Variant A: Storytelling / Problem-led / Emotional
   - Variant B: Product Demo / Benefit-led / Direct Response
4. Generate 2 Video Variants directly from the Creative Plan.
5. Review Variant A / Variant B scripts, timelines, storyboards, voiceover text, subtitle text, cover prompts, captions, and video prompts.
6. Review the Production Package / Generation Pipeline.
7. Export the Production Package or configure providers and Render Video.
8. Use Project JSON Debug to inspect the raw backend response.

Legacy angle generation is available only for backward compatibility and is not part of the main flow.

## API contract

Shared FE/BE contract: `../API_CONTRACT.md`

The main frontend flow uses `CreativePlan`, `Variant`, `VideoProductionPackage`, and `VariantGenerationPipeline`. Legacy compatibility fields may still exist in the API response, but they are not displayed as required user steps.

## Demo samples

The homepage includes a "Try Sample Inputs" panel for:

- Coin Scanner App
- Acne Serum
- Coffee Shop
- Language Learning App
