from pathlib import Path
import os

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional local convenience
    load_dotenv = None


BASE_DIR = Path(__file__).resolve().parent
BACKEND_DIR = BASE_DIR.parent
DATA_DIR = BASE_DIR / "data"
UPLOADS_DIR = BASE_DIR / "uploads"
PROJECTS_JSON = DATA_DIR / "projects.json"

if load_dotenv:
    load_dotenv(BACKEND_DIR / ".env", override=True)


def _split_secret_list(raw_value: str) -> list[str]:
    return [
        item.strip().strip('"').strip("'")
        for item in raw_value.replace("\n", ",").replace(";", ",").split(",")
        if item.strip().strip('"').strip("'")
    ]


def _read_env_file_values(names: set[str]) -> list[str]:
    env_path = BACKEND_DIR / ".env"
    if not env_path.exists():
        return []

    values: list[str] = []
    # utf-8-sig strips a Windows BOM so the first env name is not parsed as
    # "\ufeffGEMINI_API_KEYS".
    for line in env_path.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        name, raw_value = stripped.split("=", 1)
        if name.strip() in names:
            values.extend(_split_secret_list(raw_value))
    return values


def _collect_gemini_api_keys() -> list[str]:
    keys: list[str] = []
    keys.extend(_split_secret_list(os.getenv("GEMINI_API_KEYS", "")))
    keys.extend(_split_secret_list(os.getenv("GEMINI_API_KEY", "")))

    for index in range(1, 51):
        keys.extend(_split_secret_list(os.getenv(f"GEMINI_API_KEY_{index}", "")))

    names = {"GEMINI_API_KEYS", "GEMINI_API_KEY"} | {f"GEMINI_API_KEY_{index}" for index in range(1, 51)}
    keys.extend(_read_env_file_values(names))

    unique_keys: list[str] = []
    seen: set[str] = set()
    for key in keys:
        if key not in seen:
            unique_keys.append(key)
            seen.add(key)
    return unique_keys


GEMINI_API_KEYS = _collect_gemini_api_keys()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
GEMINI_API_BASE_URL = os.getenv("GEMINI_API_BASE_URL", "https://generativelanguage.googleapis.com/v1beta")
GEMINI_REQUEST_TIMEOUT_SECONDS = max(30, int(os.getenv("GEMINI_REQUEST_TIMEOUT_SECONDS", "180")))
GEMINI_TRANSIENT_MAX_ATTEMPTS = max(1, min(int(os.getenv("GEMINI_TRANSIENT_MAX_ATTEMPTS", "2")), 4))
GEMINI_RETRY_BASE_SECONDS = max(0.25, float(os.getenv("GEMINI_RETRY_BASE_SECONDS", "1.5")))
IMAGE_PROVIDER_NAME = os.getenv("IMAGE_PROVIDER_NAME", "")
IMAGE_PROVIDER_API_KEY = os.getenv("IMAGE_PROVIDER_API_KEY", "")
IMAGE_PROVIDER_BASE_URL = os.getenv("IMAGE_PROVIDER_BASE_URL", "https://api.shopaikey.com")
IMAGE_OUTPUT_SIZE = os.getenv("IMAGE_OUTPUT_SIZE", "2K")
IMAGE_GENERATION_CONCURRENCY = max(1, min(int(os.getenv("IMAGE_GENERATION_CONCURRENCY", "2")), 6))
IMAGE_GENERATION_MAX_RETRIES = max(1, min(int(os.getenv("IMAGE_GENERATION_MAX_RETRIES", "3")), 6))
IMAGE_GENERATION_RETRY_BASE_SECONDS = max(0.25, float(os.getenv("IMAGE_GENERATION_RETRY_BASE_SECONDS", "2")))
VIDEO_PROVIDER_NAME = os.getenv("VIDEO_PROVIDER_NAME", "shopaikey")
VIDEO_PROVIDER_API_KEY = os.getenv("VIDEO_PROVIDER_API_KEY", "") or IMAGE_PROVIDER_API_KEY
VIDEO_PROVIDER_BASE_URL = os.getenv("VIDEO_PROVIDER_BASE_URL", "https://api.shopaikey.com")
VIDEO_MODEL_ID = os.getenv("VIDEO_MODEL_ID", "veo3.1-pro")
VIDEO_MODEL_RATIO = os.getenv("VIDEO_MODEL_RATIO", "9:16")
VIDEO_ENHANCE_PROMPT = os.getenv("VIDEO_ENHANCE_PROMPT", "false").strip().lower() in {"1", "true", "yes", "on"}
VIDEO_ENABLE_UPSAMPLE = os.getenv("VIDEO_ENABLE_UPSAMPLE", "true").strip().lower() in {"1", "true", "yes", "on"}
VIDEO_REFERENCE_LIMIT = max(1, min(int(os.getenv("VIDEO_REFERENCE_LIMIT", "1")), 2))
VIDEO_REQUEST_TIMEOUT_SECONDS = max(15, int(os.getenv("VIDEO_REQUEST_TIMEOUT_SECONDS", "90")))
ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]


def ensure_app_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    if not PROJECTS_JSON.exists():
        PROJECTS_JSON.write_text("[]\n", encoding="utf-8")
