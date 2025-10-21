import os
from pathlib import Path

"""환경 변수에서 bool 타입을 안전하게 읽는다."""


def env_bool(name: str, default: bool = False) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    return str(v).strip().lower() in ("1", "true", "yes", "y", "on")


"""환경 변수에서 콤마/개행 구분 리스트를 안전하게 읽는다."""


def env_list(name: str, default_list):
    v = os.getenv(name)
    if not v:
        return list(default_list)
    parts = [p.strip() for p in v.replace("\n", ",").split(",") if p.strip()]
    return parts or list(default_list)


"""환경 변수에서 파일 경로를 Path 객체로 변환."""


def env_path(name: str, default: Path) -> Path:
    v = os.getenv(name)
    return Path(v) if v else default
