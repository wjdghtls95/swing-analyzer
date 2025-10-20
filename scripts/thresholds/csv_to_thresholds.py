# scripts/thresholds/csv_to_thresholds.py
from __future__ import annotations
import argparse
import json
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from app.config.settings import settings
from app.utils.resource_finder import rf


# ----------------- CLI 파서 -----------------
def _parse_args(argv=None):
    ap = argparse.ArgumentParser()
    # --csv 는 선택. 비워두면 rf.dataset_path() 사용
    ap.add_argument("--csv", required=False, help="phase_dataset.csv 경로 (생략 시 자동 탐색)")
    ap.add_argument("--out", required=True, help="출력 JSON 경로 (예: app/config/2025-10-20_thresholds.json)")
    ap.add_argument("--by", default="phase", choices=["phase", "club", "overall"])
    ap.add_argument("--metric", default=",".join(settings.THRESH_METRICS))
    ap.add_argument("--phases", default=",".join(settings.THRESH_PHASES))
    return ap.parse_args(argv)


# ----------------- 경로 해석 -----------------
def _resolve_csv_path(arg_csv: Optional[str]) -> Path:
    """--csv 미지정 시 ResourceFinder로 기본 데이터셋 경로 탐색."""
    if arg_csv:
        p = Path(arg_csv)
        return p if p.is_absolute() else (settings.ROOT / arg_csv)
    # 미지정이면 finder 사용
    return rf.dataset_path()


# ----------------- 내부 유틸 -----------------
def _to_numeric_series(s: pd.Series) -> pd.Series:
    """문자/NaN 포함 가능 시 안전 변환"""
    return pd.to_numeric(s, errors="coerce").dropna()


def _guard_and_clip(series: pd.Series, metric: str) -> pd.Series:
    """metrics 물리 범위를 settings에서 참조해 클리핑"""
    low, high = settings.METRIC_RANGES.get(metric, (None, None))
    s = _to_numeric_series(series)
    if low is not None and high is not None:
        s = s.clip(low, high)
    return s


def _build_bins(values: pd.Series, num_bins: int = 5) -> dict:
    """
    단일 메트릭에 대한 구간(bin) 요약.
    - 표본 너무 적거나 값이 비정상이면 빈 dict.
    """
    values = _to_numeric_series(values)
    if len(values) < 5:
        return {}

    # 분위 분할 (0..1)
    quantiles = np.linspace(0, 1, num_bins + 1)
    cuts = np.quantile(values, quantiles)

    # 퇴화 가드: 범위가 사실상 0
    if float(np.max(cuts) - np.min(cuts)) < 1e-6:
        return {}

    mean = float(np.round(values.mean(), 2))
    std = float(np.round(values.std(ddof=0), 2))
    return {
        "bins": [float(np.round(x, 2)) for x in cuts],
        "mean": mean,
        "std": std,
        "n": int(len(values)),
    }


# ----------------- 메인 -----------------
def main(argv=None):
    args = _parse_args(argv)

    csv_path = _resolve_csv_path(args.csv)
    if not csv_path.exists():
        raise FileNotFoundError(
            f"입력 CSV 파일이 존재하지 않습니다: {csv_path}\n"
            f"힌트) --csv를 지정하거나, .env의 DATASET_PATH 또는 "
            f"기본 {rf.dataset_path()} 위치에 파일을 두세요."
        )

    df = pd.read_csv(csv_path)
    if df.empty:
        raise ValueError(f"❌ 입력 CSV가 비어 있습니다: {csv_path}")

    metrics = [m.strip() for m in args.metric.split(",") if m.strip()]
    phases = [p.strip() for p in args.phases.split(",") if p.strip()]

    out_obj: dict = {}

    if args.by == "overall":
        section = {}
        for m in metrics:
            section[m] = _build_bins(_guard_and_clip(df[m], m))
        out_obj["overall"] = section

    elif args.by == "club":
        for club, group in df.groupby("club", dropna=True):
            section = {}
            for m in metrics:
                section[m] = _build_bins(_guard_and_clip(group[m], m))
            out_obj[str(club)] = section

    else:  # by == "phase"  (필요하면 club×phase로 바꿀 수 있음)
        for ph, group in df.groupby("phase", dropna=True):
            if ph not in phases:
                continue
            section = {}
            for m in metrics:
                section[m] = _build_bins(_guard_and_clip(group[m], m))
            out_obj[str(ph)] = section

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(out_obj, f, ensure_ascii=False, indent=2)

    print(f"[OK] thresholds -> {out_path}")


if __name__ == "__main__":
    main()