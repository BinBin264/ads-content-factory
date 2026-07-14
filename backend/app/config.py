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
    load_dotenv(BACKEND_DIR / ".env")


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
    for line in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
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


GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_API_KEYS = _collect_gemini_api_keys()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
GEMINI_API_BASE_URL = os.getenv("GEMINI_API_BASE_URL", "https://generativelanguage.googleapis.com/v1beta")
IMAGE_PROVIDER_NAME = os.getenv("IMAGE_PROVIDER_NAME", "")
IMAGE_PROVIDER_API_KEY = os.getenv("IMAGE_PROVIDER_API_KEY", "")
IMAGE_PROVIDER_BASE_URL = os.getenv("IMAGE_PROVIDER_BASE_URL", "https://api.openai.com/v1")
IMAGE_MODEL_ID = os.getenv("IMAGE_MODEL_ID", "gpt-image-1")
VIDEO_PROVIDER_NAME = os.getenv("VIDEO_PROVIDER_NAME", "")
VIDEO_PROVIDER_API_KEY = os.getenv("VIDEO_PROVIDER_API_KEY", "")
VIDEO_PROVIDER_BASE_URL = os.getenv("VIDEO_PROVIDER_BASE_URL", "https://api.gommo.net")
VIDEO_PROVIDER_DOMAIN = os.getenv("VIDEO_PROVIDER_DOMAIN", "79ai.net")
VIDEO_MODEL_ID = os.getenv("VIDEO_MODEL_ID", "veo_omni")
VIDEO_MODEL_MODE = os.getenv("VIDEO_MODEL_MODE", "flash")
VIDEO_MODEL_RATIO = os.getenv("VIDEO_MODEL_RATIO", "9:16")
VIDEO_MODEL_DURATION = os.getenv("VIDEO_MODEL_DURATION", "4")
VIDEO_MODEL_RESOLUTION = os.getenv("VIDEO_MODEL_RESOLUTION", "720p")
VIDEO_TRANSLATE_TO_EN = os.getenv("VIDEO_TRANSLATE_TO_EN", "false")
VIDEO_REFERENCE_LIMIT = int(os.getenv("VIDEO_REFERENCE_LIMIT", "4"))
VIDEO_POLL_INTERVAL_SECONDS = float(os.getenv("VIDEO_POLL_INTERVAL_SECONDS", "3.5"))
VIDEO_POLL_TIMEOUT_SECONDS = float(os.getenv("VIDEO_POLL_TIMEOUT_SECONDS", "160"))
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
