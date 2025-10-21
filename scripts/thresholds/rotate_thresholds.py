from __future__ import annotations
import argparse
from datetime import date
from pathlib import Path
import os

from app.config.settings import settings
from app.utils.resource_finder import rf
from scripts.thresholds import csv_to_thresholds


def _parse_args(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--csv",
        required=False,
        help="phase_dataset.csv 경로 (생략 시 DATASET_PATH 또는 기본값 사용)",
    )
    ap.add_argument("--by", default="phase", choices=["club", "overall", "phase"])
    ap.add_argument("--outdir", default=str(settings.CONFIG_DIR))
    ap.add_argument(
        "--namefmt", default="{date}_thresholds.json"
    )  # 예: 2025-10-20_thresholds.json
    return ap.parse_args(argv)


def _quick_qc(new_path: Path, old_path: Path | None) -> bool:
    """간단 QC: 파일 존재 + JSON 로드 가능 여부만"""
    if not new_path.exists() or new_path.stat().st_size == 0:
        print("[QC] new thresholds empty or missing")
        return False
    try:
        rf.load_json(new_path)
        return True
    except Exception as e:
        print(f"[QC] failed to load new json: {e}")
        return False


def main(argv=None):
    args = _parse_args(argv)

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    name = args.namefmt.format(date=date.today().isoformat())
    new_path = outdir / name

    # 1) 새 thresholds 생성 (모듈 직접 호출)
    build_argv = ["--out", str(new_path), "--by", args.by]
    if args.csv:
        build_argv.extend(["--csv", args.csv])
    csv_to_thresholds.main(build_argv)

    # 2) QC
    current_link = settings.CONFIG_DIR / "thresholds_current.json"
    old_path = (
        current_link.resolve()
        if current_link.exists() and current_link.is_symlink()
        else None
    )
    if not _quick_qc(new_path, old_path):
        print("[QC] failed. keep current.")
        return

    # 3) 심링크 스위치 (상대 링크)
    if current_link.exists() or current_link.is_symlink():
        current_link.unlink()
    os.chdir(outdir)  # 상대 심링크를 위해 기준 디렉토리 이동
    Path("thresholds_current.json").symlink_to(Path(name).name)
    print(f"[SWITCHED] {current_link} -> {name}")

    # 4) (선택) 오래된 버전 정리: data/thresholds/archive 보관 or 삭제는 별도 스크립트에서 수행
    #   - 여기선 건들지 않음


if __name__ == "__main__":
    main()
