"""
logs/*.json → ML 학습용 데이터셋으로 변환

logs/*.json -> 프레임별 특성 X, 라벨 y 생성
- X: (T, 9)  = [elbow, knee, spine_tilt, d1_elbow, d1_knee, d1_spine, d2_elbow, d2_knee, d2_spine]
- y: (T,)    = {0..8}  # 0:P2, 1:P3, ..., 7:P9, 8:None(라벨 부여 실패)

저장:
  artifacts/datasets/phase_X.pt
  artifacts/datasets/phase_y.pt
"""

import os, glob, json
import pandas as pd
from pathlib import Path

OUT_DIR = Path("artifacts/datasets")
OUT_DIR.mkdir(parents=True, exist_ok=True)

def main():
    files = glob.glob("logs/*.json")
    rows = []
    for f in files:
        with open(f, "r", encoding="utf-8") as fp:
            d = json.load(fp)

        # features: elbow, knee, spine_tilt (있을 경우)
        for ph, vals in (d.get("phase_metrics") or {}).items():
            row = {
                "swingId": d.get("swingId"),
                "phase": ph,
                "elbow": vals.get("elbow"),
                "knee": vals.get("knee"),
                "spine_tilt": vals.get("spine_tilt"),
                "club": d.get("input", {}).get("club"),
            }
            rows.append(row)

    df = pd.DataFrame(rows)
    out_csv = OUT_DIR / "phase_dataset.csv"
    df.to_csv(out_csv, index=False)
    print(f"[build_phase_dataset] saved: {out_csv}, rows={len(df)}")

if __name__ == "__main__":
    main()