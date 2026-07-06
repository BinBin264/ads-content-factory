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
2. Generate Creative Plan.
3. Generate 2 Video Variants.
4. Review Production Package.
5. Export / Render Video through the configured backend video provider.

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
