# AI Ads Production Factory

Full-stack MVP for turning product inputs, app screenshots, product images, logos, and brand kits into production-ready short-form AI video ad packages.

Pipeline:

1. Product / BrandKit input
2. Product Intelligence with Gemini Vision / Gemini LLM
3. Creative Angles
4. Script + basic Storyboard
5. Auto Character Planner
6. Character Bible
7. Character Reference Prompts
8. Production Scenes
9. Keyframe Prompts
10. Video Prompts
11. UI Overlay Plan
12. Edit Plan
13. Export Production Package
14. Real Render Provider

The repo does not create local video output without a configured video provider. Generate Variants creates a production package only. Export Production Package writes prompt and planning files so you can manually test image generation, image-to-video, or reference-to-video tools. Render Video only calls a real configured provider.

## Environment

Backend env:

```text
GEMINI_API_KEYS=your_key_1,your_key_2
GEMINI_MODEL=gemini-2.5-flash
VIDEO_PROVIDER_NAME=your_provider_name
VIDEO_PROVIDER_API_KEY=your_video_provider_key
```

`GEMINI_API_KEYS` is required for Product Intelligence and all content generation. If the video provider env is missing, `/render` returns a clear configuration error.

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

1. Analyze Product
2. Generate Angles
3. Generate 2 Variants
4. Review Character, Reference Prompts, Production Scenes, and Overlay / Edit Plan tabs
5. Export Production Package
6. Use the exported keyframe and video prompts in your image/video tool

Expected Coin Scanner production output includes a warm, trustworthy UGC character, five character reference prompts, four production scenes, safe estimated-value language, and the disclaimer: `Estimated reference value only. Actual value may vary.`
