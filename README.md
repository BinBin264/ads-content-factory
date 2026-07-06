# AI Ads Production Factory

Full-stack MVP for turning product inputs, app screenshots, product images, logos, and brand kits into production-ready short-form AI video ad packages.

Pipeline:

1. Product / Brand Kit Input
2. Creative Plan
3. 2 Variant Directions
4. Script + Storyboard
5. Character Bible / Reference Prompts
6. Production Scenes
7. Keyframe + Video Prompts
8. UI Overlay + Edit Plan
9. Export / Render

`Creative Plan` replaces the old separate analysis and angle-planning steps. Each project creates exactly two default variant directions:

- Variant A: Storytelling / Problem-led / Emotional
- Variant B: Product Demo / Benefit-led / Direct Response

The main flow does not ask users to generate or choose from five angles. `/angles` remains only for backward compatibility with older clients.

The repo does not create local video output without a configured video provider. Generate Variants creates a production package and a step-by-step generation pipeline. Manual mode lets you copy prompts, create assets in web tools, and upload step outputs. Render Video runs the same pipeline with real configured providers. No mock or placeholder video is created.

The generation workflow now follows three OpenMontage-inspired rules:

- `backend/app/pipeline_manifests/ad_video_generation.json` is the workflow contract for stages, required artifacts, outputs, review focus, and success criteria.
- `backend/app/services/video_provider.py` exposes a small provider registry contract for each tool type. It shows manual paths and required env, but does not fake provider output.
- Every variant pipeline carries source artifacts from earlier phases so the Creative Plan, variant direction, timeline, storyboard, production package, prompts, uploaded assets, and final exports stay connected.

## Environment

Backend env:

```text
GEMINI_API_KEYS=your_key_1,your_key_2
GEMINI_MODEL=gemini-2.5-flash
VIDEO_PROVIDER_NAME=your_provider_name
VIDEO_PROVIDER_API_KEY=your_video_provider_key
```

`GEMINI_API_KEYS` is required for Creative Plan and all content generation. If the video provider env is missing, `/render` returns a clear configuration error.

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

Docs:

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

## Coin Scanner App Test

Create a project:

```text
Product name: Coin Scanner App
Category: Mobile app
Description: An app that helps users scan old coins, identify coin details, and view estimated reference value.
Audience: People who find old coins at home, casual coin collectors, adults with coin jars.
Goal: app_install
Platform: TikTok
Duration: 20s
Tone: Natural UGC, relatable, curiosity-driven, realistic, not too polished.
CTA: Download now and scan your old coins.
Claims to avoid: Guaranteed value, 100% accurate appraisal, you will make money, this coin is definitely worth money.
```

Then run:

1. Generate Creative Plan
2. Generate 2 Video Variants
3. Review Production Package
4. Follow the Generation Pipeline cards: create character refs, upload them, create keyframes, upload clips, overlay app UI, assemble, and export
5. Export Production Package or configure providers and use Render Video / Run Full Pipeline

Expected Coin Scanner production output includes one compact Creative Plan, exactly two video variants, four scenes for 15s or five scenes for 20-30s, a warm trustworthy UGC character when needed, keyframe/video prompts, overlay/edit/export steps, safe estimated-value language, and the disclaimer: `Estimated reference value only. Actual value may vary.`
