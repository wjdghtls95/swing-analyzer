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
# Project root 탐색
#   - .git / pyproject.toml / requirements.txt 중 하나가 보이는 최상단을 루트로 간주
#   - 실패 시 BASE_DIR 환경변수 사용
# ─────────────────────────────────────────────────────────
def find_project_root() -> Path:
    cur = Path(__file__).resolve()
    for parent in cur.parents:
        if any(
            (parent / m).exists()
            for m in (".git", "pyproject.toml", "requirements.txt")
        ):
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
# .env 로딩
#   - ENV_FILE 지정 시 우선
#   - 없으면 ROOT/.env.<ENV> → 없으면 ROOT/.env
# ─────────────────────────────────────────────────────────
_DEFAULT_ENV = os.getenv("ENV", "test")
_env_file_candidate = ROOT / f".env.{_DEFAULT_ENV}"
_ENV_FILE = (
    Path(os.getenv("ENV_FILE")).resolve()
    if os.getenv("ENV_FILE")
    else (_env_file_candidate if _env_file_candidate.exists() else (ROOT / ".env"))
)
load_dotenv(dotenv_path=_ENV_FILE, override=False)


class Settings:
    # ── App / Runtime ─────────────────────────────────────
    ENV: str = os.getenv("ENV", _DEFAULT_ENV)
    FASTAPI_PORT: int = int(os.getenv("FASTAPI_PORT", 8000))
    DEBUG_MODE: bool = env_bool("DEBUG_MODE", False)

    # ── Base Paths ────────────────────────────────────────
    ROOT: Path = ROOT
    CONFIG_DIR: Path = env_path("CONFIG_DIR", ROOT / "app" / "config")
    DATA_DIR: Path = env_path("DATA_DIR", ROOT / "data")

    # ── Standard data subdirs (모두 DATA_DIR 기준) ────────
    VIDEOS_DIR: Path = DATA_DIR / "videos"
    NORMALIZED_DIR: Path = DATA_DIR / "normalized"
    DOWNLOADS_DIR: Path = DATA_DIR / "downloads"
    LOG_DIR: Path = DATA_DIR / "logs"
    OUTPUT_DIR: Path = DATA_DIR / "output"
    DATASETS_DIR: Path = DATA_DIR / "datasets"
    THRESHOLDS_ARCHIVE_DIR: Path = DATA_DIR / "thresholds" / "archive"
    REPORTS_DIR: Path = DATA_DIR / "reports"

    # 업로드(외부 입력) 기본 폴더
    UPLOADS_DIR: Path = env_path("UPLOADS_DIR", ROOT / "uploads")

    # ── Video Normalize Params ────────────────────────────
    VIDEO_FPS: int = int(os.getenv("VIDEO_FPS", DEFAULT_VIDEO_FPS))
    VIDEO_HEIGHT: int = int(os.getenv("VIDEO_HEIGHT", DEFAULT_VIDEO_HEIGHT))
    VIDEO_MIRROR: bool = env_bool("VIDEO_MIRROR", DEFAULT_VIDEO_MIRROR)

    # ── Phase detection ───────────────────────────────────
    PHASE_METHOD: str = os.getenv("PHASE_METHOD", "auto")  # "auto" | "ml" | "rule"
    PHASE_MODEL_PATH: Optional[str] = os.getenv("PHASE_MODEL_PATH")
    PHASE_MODEL_INPUT_DIM: int = 3
    PHASE_MODEL_HIDDEN_DIM: int = 32
    PHASE_MODEL_NUM_CLASSES: int = 8

    # ── Threshold / 통계용 공용 키 ───────────────────────
    THRESH_METRICS = env_list(
        "THRESH_METRICS",
        ["elbow", "knee", "spine_tilt", "shoulder_turn", "hip_turn", "x_factor"],
    )
    THRESH_PHASES = env_list(
        "THRESH_PHASES",
        ["P2", "P3", "P4", "P5", "P6", "P7", "P8", "P9"],
    )

    # 분위 구간 개수 (예: 5 → 6개 엣지로 나뉨)
    THRESH_NUM_BINS: int = int(os.getenv("THRESH_NUM_BINS", 5))
    # 최소 표본 수 (너무 적으면 빈 결과 반환)
    THRESH_MIN_N: int = int(os.getenv("THRESH_MIN_N", 5))
    # 퇴화 가드 임계값: 구간이 사실상 한 점이면 skip
    THRESH_DEGENERATE_EPS: float = float(os.getenv("THRESH_DEGENERATE_EPS", "1e-6"))

    # ── Metrics Range & Sample Guards ─────────────────────
    METRIC_RANGES = {
        "elbow": (0, 180),
        "knee": (0, 180),
        "spine_tilt": (-30, 60),
        "shoulder_turn": (-180, 180),
        "hip_turn": (-180, 180),
        "x_factor": (-60, 60),
    }
    MIN_SAMPLE = 30
    MAX_SAMPLE = 100

    # ── 명시적 파일/데이터셋 경로(선택) ───────────────────
    THRESHOLDS_FILE: Optional[str] = os.getenv("THRESHOLDS_FILE")
    DATASET_PATH: Optional[str] = os.getenv("DATASET_PATH")

    def __init__(self) -> None:
        # 자주 쓰는 디렉토리 존재 보장
        dirs = [
            self.UPLOADS_DIR,
            self.LOG_DIR,
            self.OUTPUT_DIR,
            self.DOWNLOADS_DIR,
            self.NORMALIZED_DIR,
            self.DATASETS_DIR,
            # self.THRESHOLDS_DIR,
            self.THRESHOLDS_ARCHIVE_DIR,
            self.REPORTS_DIR,
            self.VIDEOS_DIR,
        ]
        for d in dirs:
            Path(d).mkdir(parents=True, exist_ok=True)


# 전역 싱글톤처럼 사용
settings = Settings()
