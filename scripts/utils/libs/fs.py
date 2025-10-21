# scripts/libs/fs.py
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

REQUIRED_DIRS = [
    PROJECT_ROOT / "app" / "uploads",
    PROJECT_ROOT / "data" / "videos" / "pros_faceon",
    PROJECT_ROOT / "data" / "processed",
    PROJECT_ROOT / "data" / "reports",
    PROJECT_ROOT / "artifacts" / "models",
]


def ensure_dirs(paths=None):
    targets = paths or REQUIRED_DIRS
    for p in targets:
        Path(p).mkdir(parents=True, exist_ok=True)
