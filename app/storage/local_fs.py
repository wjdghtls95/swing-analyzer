from pathlib import Path
from typing import Iterable

class LocalFS:
    def __init__(self, root: Path):
        self.root = Path(root)

    def glob_videos(self, rel: str | Path, exts: Iterable[str] = (".mp4", ".mov", ".mkv")):
        base = (self.root / rel).resolve()
        for p in base.rglob("*"):
            if p.suffix.lower() in exts:
                yield p

    def rel_from(self, p: Path) -> str:
        return str(p.resolve().relative_to(self.root.resolve()))