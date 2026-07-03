# API Contract

Shared project shape for backend and frontend integration.

```json
{
  "project": {
    "id": "project_001",
    "product_name": "Coin Scanner App",
    "product_category": "mobile app",
    "product_description": "An app that scans old coins and shows coin details and estimated reference value.",
    "audience": "people who find old coins at home",
    "goal": "app_install",
    "platform": "tiktok",
    "duration": "20s",
    "tone": "UGC, natural, realistic",
    "cta": "Download now",
    "claims_to_avoid": ["guaranteed value", "100% accurate appraisal"],
    "brand_colors": ["#1E88E5", "#FFFFFF"],
    "uploaded_files": [],
    "product_brief": {},
    "creative_angles": [],
    "variants": [],
    "created_at": "2026-07-02T00:00:00",
    "updated_at": "2026-07-02T00:00:00"
  }
}
```

For `POST /api/projects`, the frontend sends multipart form data. Array fields are sent as repeated fields:

```text
claims_to_avoid=guaranteed value
claims_to_avoid=100% accurate appraisal
brand_colors=#1E88E5
brand_colors=#FFFFFF
```

The backend also accepts comma, semicolon, or newline-separated values for compatibility, then stores and returns arrays.
