import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

from app.analyze.constants import DEFAULT_VIDEO_FPS, DEFAULT_VIDEO_HEIGHT, DEFAULT_VIDEO_MIRROR

# ─────────────────────────────────────────────────────────
#    .env 로딩 전략 (실행 환경에 따라 자동 선택)
#    - ENV_FILE 가 지정되면 그걸 사용
#    - 아니면 .env.<ENV> 가 있으면 사용, 없으면 .env
# ─────────────────────────────────────────────────────────
_DEFAULT_ENV = os.getenv("ENV", "test")  # dev | test | prod 등
_ENV_FILE_CANDIDATE = f".env.{_DEFAULT_ENV}"
_ENV_FILE = os.getenv("ENV_FILE") or (_ENV_FILE_CANDIDATE if os.path.exists(_ENV_FILE_CANDIDATE) else ".env")
load_dotenv(dotenv_path=_ENV_FILE)

def _env_bool(name: str, default: bool = False) -> bool:
    return (os.getenv(name, str(default))).strip().lower() in ("1", "true", "yes", "y", "on")

def _env_path(name: str, default: Path) -> Path:
    v = os.getenv(name)
    return Path(v) if v else default

class Settings:
    # ── App / Runtime ─────────────────────────────────────
    ENV: str = os.getenv("ENV", _DEFAULT_ENV)            # dev|test|prod
    FASTAPI_PORT: int = int(os.getenv("FASTAPI_PORT", 8000))
    DEBUG_MODE: bool = _env_bool("DEBUG_MODE", False)

    # ── Paths ─────────────────────────────────────────────
    ROOT: Path = Path(__file__).resolve().parents[2]
    UPLOADS_DIR: Path = _env_path("UPLOADS_DIR", ROOT / "uploads")
    OUTPUT_DIR: Path  = _env_path("OUTPUT_DIR",  ROOT / "data" / "output")

    # ── Video Normalize Params ────────────────────────────
    VIDEO_FPS: int = int(os.getenv("VIDEO_FPS", DEFAULT_VIDEO_FPS))
    VIDEO_HEIGHT: int = int(os.getenv("VIDEO_HEIGHT", DEFAULT_VIDEO_HEIGHT))
    VIDEO_MIRROR: bool = _env_bool("VIDEO_MIRROR", DEFAULT_VIDEO_MIRROR)  # 좌/우타, 카메라 각 보정시

    # ── Phase detection ──────
    PHASE_METHOD: str = os.getenv("PHASE_METHOD", "auto")  # "auto" | "ml" | "rule"
    PHASE_MODEL_PATH: Optional[str] = os.getenv("PHASE_MODEL_PATH")  # 없으면 rule fallback
    PHASE_MODEL_INPUT_DIM: int = 3
    PHASE_MODEL_HIDDEN_DIM: int = 32
    PHASE_MODEL_NUM_CLASSES: int = 8

    # ── (옵션) 외부 연동/스토리지/DB/큐 등 ───────────────
    # DATABASE_URL: str | None = os.getenv("DATABASE_URL")
    # REDIS_URL: str | None = os.getenv("REDIS_URL")
    # PLATFORM_API_BASE: str | None = os.getenv("PLATFORM_API_BASE")
    # PLATFORM_API_TOKEN: str | None = os.getenv("PLATFORM_API_TOKEN")

    def __init__(self) -> None:
        # 디렉토리 존재 보장 (앱 시작 시 1회)
        self.UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
        self.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 전역 싱글톤처럼 사용
settings = Settings()