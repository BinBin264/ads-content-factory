# AI Ads Production Factory

Full-stack MVP for turning a product brief, product images, app screenshots, logos, and moodboards into a copy-ready AI video ad plan.

Current flow:

```text
Create Project
-> Brief Input
-> Upload References
-> Plan Creation
-> Character / Location / Keyframe references
-> 4-second scene clips
-> Manual video testing in Kling / other video tools
```

`Plan Creation` is now the central output. It contains:

- Product lock rules so uploaded references are not redesigned.
- Product reference map for uploaded files.
- Primary character and primary location reference prompts.
- 4-second scene clips split from the script.
- Keyframe/image prompts per scene.
- Final video prompt per scene.
- Voice lines, overlay text, timing beats, camera direction, and negative rules.

There is no separate variant generation, package export, or local fake video output flow in the current MVP. After Plan Creation, the user creates/selects character, location, and keyframe references, then copies each 4-second scene prompt into Flow, Kling, or another video model UI for manual testing. Provider automation can be added later on top of the same scene schema.

## Environment

Backend env:

```text
GEMINI_API_KEYS=your_key_1,your_key_2
GEMINI_MODEL=gemini-2.5-flash
```

`GEMINI_API_KEYS` is required. The backend rotates configured Gemini keys per request and retries the next key on quota, auth, rate-limit, or provider errors. There is no fallback mock LLM.

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
Brief: Create a 20s vertical UGC ad for people who find old coins at home. The story should start with curiosity, show the app scan flow from uploaded screenshots, keep safe estimated-value language, and end with a download CTA. Avoid guaranteed appraisal or money-making claims.
Uploads: app scan screenshot, app result screenshot, logo, or product references.
```

Then run:

1. Create Project.
2. Upload product/app references inside the project workflow.
3. Generate Plan Creation.
4. Review product lock, primary character, primary location, and reference map.
5. For each 4-second scene, create/pick keyframe images.
6. In Manual mode, copy the final 4-second scene video prompt into Flow, Kling, or another video generation UI.
7. In Automation mode, configure `VIDEO_PROVIDER_NAME=79ai` and `VIDEO_PROVIDER_API_KEY`, then generate one VEO Omni Flash `9:16` `4s` clip per scene from the uploaded ingredients.
8. Keep the negative rules and reference image mapping attached to every manual generation.
