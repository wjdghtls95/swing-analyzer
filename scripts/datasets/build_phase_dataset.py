# scripts/datasets/build_phase_dataset.py
from __future__ import annotations
import json, glob
from pathlib import Path
import pandas as pd

from app.config.settings import settings


def main():
    # 1) 입력 로그 경로: settings.LOG_DIR/*.json
    files = glob.glob(str(settings.LOG_DIR / "*.json"))
    rows = []

    # 2) 로그 → 행 변환
    for fp in files:
        try:
            d = json.loads(Path(fp).read_text(encoding="utf-8"))
        except Exception:
            continue

        swing_id = d.get("swingId")
        club = (d.get("input") or {}).get("club")
        phase_metrics = d.get("phase_metrics") or {}

        # 각 phase별로 한 줄씩 적재
        for ph, vals in phase_metrics.items():
            rows.append(
                {
                    "swingId": swing_id,
                    "phase": ph,  # 예: P2..P9
                    "club": str(club) if club is not None else None,
                    "elbow": vals.get("elbow"),
                    "knee": vals.get("knee"),
                    "spine_tilt": vals.get("spine_tilt"),
                    "shoulder_turn": vals.get("shoulder_turn"),
                    "hip_turn": vals.get("hip_turn"),
                    "x_factor": vals.get("x_factor"),
                }
            )

    df = pd.DataFrame(rows)

    # 3) 최소 컬럼 보장 및 정리
    needed_cols = [
        "swingId",
        "phase",
        "club",
        "elbow",
        "knee",
        "spine_tilt",
        "shoulder_turn",
        "hip_turn",
        "x_factor",
    ]
    for c in needed_cols:
        if c not in df.columns:
            df[c] = pd.NA

    # 4) (선택) 물리 범위 가드: settings.METRIC_RANGES 적용
    rng = settings.METRIC_RANGES
    for m in ["elbow", "knee", "spine_tilt", "shoulder_turn", "hip_turn", "x_factor"]:
        if m in df.columns:
            s = pd.to_numeric(df[m], errors="coerce")
            lo, hi = rng.get(m, (None, None))
            if lo is not None and hi is not None:
                s = s.clip(lo, hi)
            df[m] = s

    # 5) 출력: artifacts/datasets/phase_dataset.csv
    out_dir = settings.DATASETS_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    out_csv = out_dir / "phase_dataset.csv"
    df.to_csv(out_csv, index=False)
    print(f"[build_phase_dataset] saved: {out_csv} rows={len(df)}")


if __name__ == "__main__":
    main()
