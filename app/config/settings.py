from __future__ import annotations
import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# helpers
from app.config.env_utils import env_bool, env_path, env_list
from app.analyze.constants import (
    DEFAULT_VIDEO_FPS,
    DEFAULT_VIDEO_HEIGHT,
    DEFAULT_VIDEO_MIRROR,
)

# ─────────────────────────────────────────────────────────
# 0) 루트 탐색 (하드코딩 제거)
#    - .git / pyproject.toml / requirements.txt 탐색
#    - 다 없으면 ENV: BASE_DIR 사용
#    - 그래도 없으면 명확히 예외 (의도치 않은 / 루트 방지)
# ─────────────────────────────────────────────────────────
def find_project_root() -> Path:
    cur = Path(__file__).resolve()
    for parent in cur.parents:
        if any((parent / marker).exists() for marker in [".git", "pyproject.toml", "requirements.txt"]):
            return parent

    env_root = os.getenv("BASE_DIR")
    if env_root:
        return Path(env_root).resolve()

    raise RuntimeError(
        "프로젝트 루트를 찾을 수 없습니다. "
        "루트에 .git/pyproject.toml/requirements.txt 중 하나를 두거나, "
        "환경변수 BASE_DIR을 지정하세요."
    )

ROOT: Path = find_project_root()

# ─────────────────────────────────────────────────────────
# 1) .env 로딩 전략 (실행 환경에 따라 자동 선택)
#    - ENV_FILE 가 지정되면 그걸 사용
#    - 아니면 ROOT 기준 .env.<ENV> 가 있으면 사용, 없으면 .env
#    ※ 기존 코드의 로직을 유지하되, 상대경로가 아닌 ROOT 기준으로 고정
# ─────────────────────────────────────────────────────────
_DEFAULT_ENV = os.getenv("ENV", "test")  # dev | test | prod 등

_ENV_FILE_CANDIDATE = ROOT / f".env.{_DEFAULT_ENV}"

_ENV_FILE = Path(os.getenv("ENV_FILE")).resolve() \
if os.getenv("ENV_FILE") \
    else (_ENV_FILE_CANDIDATE if _ENV_FILE_CANDIDATE.exists() else (ROOT / ".env"))

load_dotenv(dotenv_path=_ENV_FILE, override=False)

class Settings:
    # ── App / Runtime ─────────────────────────────────────
    ENV: str = os.getenv("ENV", _DEFAULT_ENV)            # dev|test|prod
    FASTAPI_PORT: int = int(os.getenv("FASTAPI_PORT", 8000))
    DEBUG_MODE: bool = env_bool("DEBUG_MODE", False)

    # ── Paths ─────────────────────────────────────────────
    # 하드코딩 제거: ROOT는 find_project_root() 결과
    ROOT: Path = ROOT
    # 아래 4개는 네가 올린 ResourceFinder가 기대하는 필드임
    CONFIG_DIR: Path = env_path("CONFIG_DIR", ROOT / "app" / "config")
    DATA_DIR: Path = env_path("DATA_DIR", ROOT / "dataset")
    ARTIFACTS_DIR: Path = env_path("ARTIFACTS_DIR", ROOT / "artifacts")
    LOG_DIR: Path = env_path("LOG_DIR", ROOT / "logs")

    UPLOADS_DIR: Path = env_path("UPLOADS_DIR", ROOT / "uploads")
    OUTPUT_DIR: Path  = env_path("OUTPUT_DIR",  ROOT / "data" / "output")

    # 전처리/다운로드 표준 디렉터리
    NORMALIZED_DIR: Path = env_path("NORMALIZED_DIR", ROOT / "normalized")
    DOWNLOADS_DIR: Path = env_path("DOWNLOADS_DIR", ROOT / "downloads")

    # ── Video Normalize Params ────────────────────────────
    VIDEO_FPS: int = int(os.getenv("VIDEO_FPS", DEFAULT_VIDEO_FPS))
    VIDEO_HEIGHT: int = int(os.getenv("VIDEO_HEIGHT", DEFAULT_VIDEO_HEIGHT))
    VIDEO_MIRROR: bool = env_bool("VIDEO_MIRROR", DEFAULT_VIDEO_MIRROR)  # 좌/우타, 카메라 각 보정시

    # ── Phase detection ──────
    PHASE_METHOD: str = os.getenv("PHASE_METHOD", "auto")  # "auto" | "ml" | "rule"
    PHASE_MODEL_PATH: Optional[str] = os.getenv("PHASE_MODEL_PATH")  # 없으면 rule fallback
    PHASE_MODEL_INPUT_DIM: int = 3
    PHASE_MODEL_HIDDEN_DIM: int = 32
    PHASE_MODEL_NUM_CLASSES: int = 8

    # ── Threshold / 통계용 공용 키 ───────────────────────
    THRESH_METRICS = env_list(
        "THRESH_METRICS",
        ["elbow", "knee", "spine_tilt", "shoulder_turn", "hip_turn", "x_factor"]
    )

    THRESH_PHASES = env_list(
        "THRESH_PHASES",
        ["P2", "P3", "P4", "P5", "P6", "P7", "P8", "P9"]
    )

    # ── Metrics Range & Sample Guards ─────────────────────────
    # 물리적 범위 (인체 한계 + 포즈 추정 오차 허용)
    METRIC_RANGES = {
        "elbow": (0, 180),
        "knee": (0, 180),
        "spine_tilt": (-30, 60),
        "shoulder_turn": (-180, 180),
        "hip_turn": (-180, 180),
        "x_factor": (-60, 60),
    }

    # 표본 가드: thresholds 생성시 기준
    MIN_SAMPLE = 30     # 표본 n < 30 → skip
    MAX_SAMPLE = 100    # 표본 n > 100 → 최근 100개만 사용

    # 명시적 파일/데이터셋 경로 (없으면 finder가 자동탐색)
    THRESHOLDS_FILE: Optional[str] = os.getenv("THRESHOLDS_FILE")
    DATASET_PATH: Optional[str] = os.getenv("DATASET_PATH")

    # ── (옵션) 외부 연동/스토리지/DB/큐 등 ───────────────
    # DATABASE_URL: str | None = os.getenv("DATABASE_URL")
    # REDIS_URL: str | None = os.getenv("REDIS_URL")
    # PLATFORM_API_BASE: str | None = os.getenv("PLATFORM_API_BASE")
    # PLATFORM_API_TOKEN: str | None = os.getenv("PLATFORM_API_TOKEN")

    def __init__(self) -> None:
        # 디렉토리 존재 보장 (앱 시작 시 1회)
        for dir in [
            self.UPLOADS_DIR, self.OUTPUT_DIR, self.LOG_DIR,
            self.ARTIFACTS_DIR, self.NORMALIZED_DIR, self.DOWNLOADS_DIR
        ]:
            dir.mkdir(parents=True, exist_ok=True)

# 전역 싱글톤처럼 사용
settings = Settings()