# scripts/thresholds/rotate_thresholds.py
from __future__ import annotations
import argparse
import json
import subprocess
from datetime import date
from pathlib import Path

from app.config.settings import settings

def _parse_args(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=False, help="phase_dataset.csv 경로 (생략 시 DATASET_PATH 또는 기본값 사용)")
    ap.add_argument("--by", default="phase", choices=["club", "overall", "phase"])
    ap.add_argument("--outdir", default=str(settings.CONFIG_DIR))
    ap.add_argument("--namefmt", default="{date}_thresholds.json")  # 예: 2025-10-20_thresholds.json
    return ap.parse_args(argv)

def _load_json(p: Path):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None

def _quick_qc(new_path: Path) -> bool:
    new = _load_json(new_path) or {}
    if not new:
        print("[QC] new thresholds empty")
        return False
    return True

def main(argv=None):
    args = _parse_args(argv)

    # CSV 경로 해석
    csv_arg = args.csv or settings.DATASET_PATH or (settings.DATA_DIR / "datasets" / "phase_dataset.csv")
    csv_path = Path(csv_arg)
    if not csv_path.is_absolute():
        csv_path = (settings.ROOT / csv_path).resolve()
    if not csv_path.exists():
        raise FileNotFoundError(f"입력 CSV가 없습니다: {csv_path}")

    outdir = Path(args.outdir)
    if not outdir.is_absolute():
        outdir = (settings.ROOT / outdir).resolve()
    outdir.mkdir(parents=True, exist_ok=True)

    name = args.namefmt.format(date=date.today().isoformat())
    new_path = outdir / name

    # 1) 새 파일 생성 (모듈 방식으로 실행)
    cmd = [
        "python", "-m", "scripts.thresholds.csv_to_thresholds",
        "--csv", str(csv_path),
        "--out", str(new_path),
        "--by", args.by,
    ]
    subprocess.check_call(cmd)

    # 2) QC
    if not _quick_qc(new_path):
        print("[QC] failed. keep current.")
        return

    # 3) 심볼릭 링크 스위치
    current_link = outdir / "thresholds_current.json"
    if current_link.exists() or current_link.is_symlink():
        current_link.unlink()
    # 상대 링크 생성
    current_link.symlink_to(new_path.name)
    print(f"[SWITCHED] {current_link} -> {new_path.name}")

if __name__ == "__main__":
    main()