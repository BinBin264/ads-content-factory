# AI Ads Content Factory MVP

AI Ads Content Factory is a full-stack MVP for turning minimal product input, brand kit assets, screenshots, or product images into short-form video ad concepts.

The current flow is:

1. Create project with product details and uploads.
2. Analyze product through a mock Product Intelligence Layer.
3. Generate five creative angles.
4. Generate two video ad variants with script, storyboard, scene prompts, title, caption, and cover prompt.
5. Mock render placeholder output files for 9:16 and 1:1 exports.

No real AI API is required for this version. The backend uses mock providers and rule-based playbooks, but the architecture is ready to swap in real LLM, Vision, image, and video providers later.

If `GEMINI_API_KEY` is configured, the backend uses Gemini for:

- Product Intelligence
- Creative Angles
- Script + Storyboard

If the key is missing or Gemini returns invalid JSON, the backend falls back to the local rule-based providers.

## Product Intelligence Layer

The backend analyzes:

- Product name, category, description, audience, goal, CTA, and claims to avoid
- Uploaded file names and content types
- Brand colors
- Product-type keywords

It then creates:

- `VisionAnalysis`
- `ProductIntelligenceBrief`
- legacy `ProductBrief` for compatibility
- recommended playbooks for mobile apps, skincare, F&B, ecommerce, education, or general UGC

## Run Backend

```powershell
cd backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

If the venv does not exist:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

Gemini setup:

```powershell
cd backend
Copy-Item .env.example .env
notepad .env
```

Set:

```text
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash
```

Backend docs:

```text
http://localhost:8000/docs
```

## Run Frontend

```powershell
cd frontend
npm install
npm run dev
```

Frontend:

```text
http://127.0.0.1:5173
```

## Demo Sample Inputs

Use the frontend "Try Sample Inputs" panel or enter:

```text
Product name: Coin Scanner App
Category: Mobile app
Description: An app that helps users scan old coins, identify coin details, and view estimated reference value.
Audience: People who find old coins at home, casual collectors.
Goal: app_install
CTA: Download now and scan your old coins.
Claims to avoid: Guaranteed value, 100% accurate appraisal, you will make money.
```

Then run:

1. Analyze Product
2. Generate Angles
3. Generate 2 Variants
4. Mock Render

Expected first two hooks:

- `I almost spent this old coin...`
- `Here's how to check an old coin in 5 seconds.`

Mock render creates output files under:

```text
backend/app/outputs/{project_id}/{variant_id}/
```

Files include `storyboard.json`, `script.txt`, `prompts.txt`, `caption.txt`, `mock_video_9x16.txt`, and `mock_video_1x1.txt`.
