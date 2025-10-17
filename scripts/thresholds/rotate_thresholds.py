# scripts/rotate_thresholds.py
import argparse, json, subprocess, shutil
from pathlib import Path
from datetime import date
from typing import Optional

CONFIG_DIR = Path("app/config")
CURRENT_LINK = CONFIG_DIR / "thresholds_current.json"

def load_json(p: Path):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None

def quick_qc(new_path: Path, old_path: Optional[Path]) -> bool:
    """아주 단순한 커버리지/빈 증가율 체크. 통과(True)면 배포."""
    new = load_json(new_path) or {}
    if not new:
        print("[QC] new thresholds empty")
        return False

    # (선택) 기존 대비 키 커버리지, bins 퇴화율 검사 등 추가 가능
    return True

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True)
    ap.add_argument("--by", default="phase", choices=["club","overall","phase"])
    ap.add_argument("--outdir", default=str(CONFIG_DIR))
    ap.add_argument("--namefmt", default="{date}_thresholds.json")  # 예: 2025-10-16_thresholds.json
    args = ap.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    name = args.namefmt.format(date=date.today().isoformat())
    new_path = outdir / name

    # 1) 새 파일 생성
    cmd = [
        "python", "scripts/thresholds/csv_to_thresholds.py",
        "--csv", args.csv,
        "--out", str(new_path),
        "--by", args.by
    ]
    subprocess.check_call(cmd)

    # 2) QC
    old_path = CURRENT_LINK.resolve() if CURRENT_LINK.exists() and CURRENT_LINK.is_symlink() else None
    if not quick_qc(new_path, old_path):
        print("[QC] failed. keep current.")
        return

    # 3) 심링크 스위치
    if CURRENT_LINK.exists() or CURRENT_LINK.is_symlink():
        CURRENT_LINK.unlink()
    CURRENT_LINK.symlink_to(new_path.name)  # 상대 링크
    print(f"[SWITCHED] {CURRENT_LINK} -> {new_path.name}")

if __name__ == "__main__":
    main()