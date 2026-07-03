# AI Ads Content Factory MVP

AI Ads Content Factory is a full-stack MVP for turning minimal product input, brand kit assets, screenshots, or product images into short-form video ad concepts.

The current flow is:

1. Create project with product details and uploads.
2. Analyze product through Gemini Vision and Product Intelligence.
3. Generate five creative angles.
4. Generate two video ad variants with script, storyboard, scene prompts, title, caption, and cover prompt.
5. Render video through a configured video provider.

Gemini is required for text and vision intelligence. Video rendering requires a configured production video provider.

If `GEMINI_API_KEYS` or legacy `GEMINI_API_KEY` is configured, the backend uses Gemini for:

- Product Intelligence
- Creative Angles
- Script + Storyboard

If all keys are missing or Gemini returns invalid JSON, the backend returns an API error so the user knows Gemini is not configured correctly.

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
GEMINI_API_KEYS=your_first_gemini_api_key,your_second_gemini_api_key
GEMINI_MODEL=gemini-2.5-flash
```

The backend rotates configured Gemini keys per request and retries the next key when Gemini returns quota, rate-limit, auth, or provider errors.

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

## Demo Input

Enter:

```text
Product name: Coin Scanner App
Category: Mobile app
Description: An app that helps users scan old coins, identify coin details, and view estimated reference value.
Campaign objective: Get app installs
CTA: Download now and scan your old coins.
Claims to avoid: Guaranteed value, 100% accurate appraisal, you will make money.
```

Then run:

1. Analyze Product
2. Generate Angles
3. Generate 2 Variants
4. Render Video

Expected first two hooks:

- `I almost spent this old coin...`
- `Here's how to check an old coin in 5 seconds.`

Video render requires `VIDEO_PROVIDER_NAME` and `VIDEO_PROVIDER_API_KEY`. No local video output is generated without a provider.
