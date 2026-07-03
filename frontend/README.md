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

1. Create a project with product details and optional uploads.
2. Analyze Product to create a Product Intelligence Brief.
3. Generate Angles to create five creative angle cards.
4. Select two angles or leave selection incomplete so the backend auto-selects.
5. Generate 2 Variants to create scripts, storyboards, prompts, captions, and cover prompts.
6. Mock Render to create placeholder export URLs for 9:16 and 1:1 outputs.
7. Use Project JSON Debug to inspect the raw backend response.

## API contract

Shared FE/BE contract: `../API_CONTRACT.md`

The Product Brief response uses arrays for `target_audience`, `emotional_triggers`, `functional_benefits`, `proof_elements`, `safe_claims`, `claims_to_avoid`, and `recommended_ad_formats`.

The UI also displays the richer `product_intelligence` response when available, with fallback to the legacy Product Brief.

## Demo samples

The homepage includes a "Try Sample Inputs" panel for:

- Coin Scanner App
- Acne Serum
- Coffee Shop
- Language Learning App
