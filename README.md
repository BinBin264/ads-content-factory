# AI Video Factory

Full-stack MVP for turning either a video ad brief or a content idea into a copy-ready AI video production plan.

Current flow:

```text
Create Project
-> Brief Input
-> Upload References
-> Plan Creation
-> Character / Location / Keyframe references
-> timed scene clips
-> Take review and continuity handoff
-> Manual video testing in Kling / other video tools
```

`Plan Creation` is now the central output. It contains:

- Product lock rules so uploaded references are not redesigned.
- Product reference map for uploaded files.
- Primary character and primary location reference prompts.
- Timed scene clips split from the script. Each scene can use a 4s, 6s, 8s, or 10s provider duration based on action complexity.
- Keyframe/image prompts per scene.
- Final video prompt per scene.
- Voice lines, overlay text, timing beats, camera direction, and negative rules.
- A story spine and world bible that keep character, wardrobe, location, product geometry, lighting, and atmosphere consistent.
- One shot contract per scene: one visible beat, a changed endpoint, continuity locks, reference roles, and reserved future beats.
- A compact provider prompt compiler and deterministic prompt quality gate instead of sending the whole plan to Veo.
- Take review with accepted observed state; rejected footage never updates continuity canon.

The continuity layer is adapted from the production-state ideas in the local `seedance-2.0` skill source, but it is provider-neutral and targets the current Google Veo workflow. It improves consistency through canonical references, per-scene re-anchoring, scoped prompts, and accepted-take handoffs. It does not claim that Veo can permanently guarantee a face, object, UI, or location across arbitrary generations.

There is no separate variant generation, package export, or local fake video output flow in the current MVP. After Plan Creation, the user creates/selects character, location, and keyframe references, then copies each timed scene prompt into Flow, Kling, or another video model UI for manual testing. In automation mode, ShopAIKey generates both reference/keyframe images and scene clips.

## Environment

Backend env:

```text
GEMINI_API_KEYS=your_key_1,your_key_2
GEMINI_MODEL=gemini-2.5-flash
GEMINI_REQUEST_TIMEOUT_SECONDS=180
GEMINI_TRANSIENT_MAX_ATTEMPTS=2
GEMINI_RETRY_BASE_SECONDS=1.5
IMAGE_PROVIDER_NAME=shopaikey-google
IMAGE_PROVIDER_API_KEY=your_image_provider_key
IMAGE_PROVIDER_BASE_URL=https://api.shopaikey.com
IMAGE_OUTPUT_SIZE=2K
IMAGE_GENERATION_CONCURRENCY=2
IMAGE_GENERATION_MAX_RETRIES=3
IMAGE_GENERATION_RETRY_BASE_SECONDS=2
VIDEO_PROVIDER_NAME=shopaikey
VIDEO_PROVIDER_BASE_URL=https://api.shopaikey.com
VIDEO_MODEL_ID=veo3.1-pro
VIDEO_MODEL_RATIO=9:16
VIDEO_ENHANCE_PROMPT=false
VIDEO_ENABLE_UPSAMPLE=true
VIDEO_REFERENCE_LIMIT=1
```

`VIDEO_MODEL_ID` is the Phase 3 default. Automation mode can override it per scene with `veo3.1-pro`, `veo3.1-fast`, `veo3.1-fast-components`, `grok-video-3`, or `grok-video-3-10s`.

Uploaded image understanding, Plan Creation, scene rewrites, keyframe prompts, and final scene prompts use Gemini exclusively. The optional ShopAIKey Gemini Image integration is isolated behind `IMAGE_PROVIDER_*` and is used only by automation-mode image generation. Image generation runs as asynchronous jobs: multiple cards can be queued together, the configured worker limit controls parallel calls, and temporary provider rate limits are retried serially.

Automation image phases require a per-job selection from `nano-banana`, `nano-banana-2`, `nano-banana-pro`, `gpt-image-1-mini`, `gpt-image-1`, `gpt-image-1.5`, and `gpt-image-2`. The backend does not choose an image model from env. Nano Banana keeps an exact `9:16` request; GPT Image uses its supported `2:3` portrait canvas and protects a centered `9:16` safe area.

There is no fallback mock LLM.

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
5. For each scene, create/pick one keyframe image.
6. In Manual mode, copy the final timed scene video prompt into Flow, Kling, or another video generation UI.
7. In Automation mode, generate one ShopAIKey `veo3.1-pro` `9:16` clip per scene in first-frame mode. The selected keyframe is uploaded and sent as the single `metadata.images` visual anchor. `VIDEO_PROVIDER_API_KEY` is optional when it shares `IMAGE_PROVIDER_API_KEY`.
8. Review the generated/uploaded take as Keep, Fix in post, Edit, Re-roll, Rewrite, or Reject. Only Keep/Fix in post becomes continuity canon for the next scene.
9. Keep the negative rules and reference image mapping attached to every manual generation.
