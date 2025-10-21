import argparse
from pathlib import Path


def parse_args():
    p = argparse.ArgumentParser(description="Aggregate swing logs to a flat table")
    p.add_argument("--glob", default="logs/*.json")
    p.add_argument("--out", default="artifacts/aggregated.csv")
    p.add_argument("--club")
    p.add_argument("--phase-method", dest="phase_method")
    p.add_argument("--since")
    p.add_argument("--until")
    return p.parse_args()


def ensure_parent_dir(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
