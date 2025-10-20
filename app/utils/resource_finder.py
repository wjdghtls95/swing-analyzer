from __future__ import annotations
from pathlib import Path
from typing import Iterable, Optional, Union, List
import glob
import json
import os

from app.config.settings import settings  # Settings 싱글톤 사용


class ResourceFinder:
    """중앙 경로 헬퍼: config/data/logs/artifacts/thresholds 관리"""
    def __init__(self):
        self.root: Path = settings.ROOT
        # settings에 상대경로로 설정되어 있으므로 아래처럼 정확히 결합
        self.data = self.root / settings.DATA_DIR
        self.config = self.root / settings.CONFIG_DIR
        self.artifacts = self.root / settings.ARTIFACTS_DIR
        self.logs = self.root / settings.LOG_DIR

        # 로그/아티팩트 폴더는 기본 생성
        self.artifacts.mkdir(parents=True, exist_ok=True)
        self.logs.mkdir(parents=True, exist_ok=True)

    # ----- 하위 경로 -----
    def under_root(self, *parts: Union[str, Path]) -> Path:
        return (self.root.joinpath(*parts)).resolve()

    def under_data(self, *parts: Union[str, Path]) -> Path:
        return (self.data.joinpath(*parts)).resolve()

    def under_config(self, *parts: Union[str, Path]) -> Path:
        return (self.config.joinpath(*parts)).resolve()

    def under_artifacts(self, *parts: Union[str, Path]) -> Path:
        return (self.artifacts.joinpath(*parts)).resolve()

    def under_logs(self, *parts: Union[str, Path]) -> Path:
        return (self.logs.joinpath(*parts)).resolve()

    # ----- glob & 최신 파일 -----
    def glob(self, pattern: str, base: Optional[Path] = None) -> List[Path]:
        base = (base or self.root)
        return [Path(p) for p in glob.glob(str(base / pattern))]

    def latest_by_mtime(self, paths: Iterable[Union[str, Path]]) -> Optional[Path]:
        paths = [Path(p) for p in paths]
        paths = [p for p in paths if p.exists()]
        return max(paths, key=lambda p: p.stat().st_mtime) if paths else None

    # ----- JSON -----
    def load_json(self, path: Union[str, Path]) -> dict:
        p = Path(path)
        with p.open("r", encoding="utf-8") as f:
            return json.load(f)

    def dump_json(self, path: Union[str, Path], obj: dict, *, indent: int = 2) -> Path:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=indent)
        return p

    # ----- thresholds / dataset 헬퍼 (ENV 최우선) -----
    def thresholds_path(self) -> Path:
        # 1) ENV 최우선
        env_path = os.getenv("THRESHOLDS_FILE")
        if env_path:
            p = Path(env_path)
            if not p.is_absolute():
                p = self.root / env_path
            if p.exists():
                return p

        # 2) current → 최신본 탐색
        current = self.under_config("thresholds_current.json")
        if current.exists():
            try:
                return current.resolve(strict=True)
            except Exception:
                return current

        latest = self.latest_by_mtime(self.glob("*_thresholds.json", base=self.config))
        return latest or current

    def dataset_path(self) -> Path:
        env_path = os.getenv("DATASET_PATH")
        if env_path:
            p = Path(env_path)
            return p if p.is_absolute() else (self.root / env_path)
        return self.under_root("dataset/phase_dataset.csv")


# 전역 인스턴스
rf = ResourceFinder()