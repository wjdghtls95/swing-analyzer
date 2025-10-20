# scripts/thresholds/csv_to_thresholds.py
import argparse, json
from pathlib import Path
import pandas as pd
import numpy as np

from app.config.settings import settings

DEFAULT_METRICS = settings.THRESH_METRICS
DEFAULT_PHASE_KEYS = settings.THRESH_PHASES
METRIC_RANGES = settings.METRIC_RANGES
MIN_SAMPLE = settings.MIN_SAMPLE
MAX_SAMPLE = settings.MAX_SAMPLE

try:
    from dotenv import load_dotenv
    load_dotenv()  # 있으면 읽고, 없으면 무시
except Exception:
    pass


def to_numeric_series(series: pd.Series) -> pd.Series:
    """문자/NaN 제거 후 float 시리즈로 변환"""
    s = pd.to_numeric(series, errors="coerce").dropna()
    return s.astype(float)


def _guard_and_clip(series: pd.Series, metric: str) -> pd.Series:
    """물리적 범위 가드 및 정리"""
    s = to_numeric_series(series)
    if metric in METRIC_RANGES:
        lo, hi = METRIC_RANGES[metric]
        s = s[(s >= lo) & (s <= hi)]
    return s


def build_bins(series: pd.Series):
    """
    시리즈의 사분위수 기반 5단계 구간(bins) 계산.
    퇴화(q90≈q10) 시 None 반환.
    """
    s = to_numeric_series(series)
    if s.empty:
        return None

    q10, q25, q75, q90 = np.percentile(s, [10, 25, 75, 90])

    # 분산 퇴화 가드
    if abs(q90 - q10) < 1e-6:
        return None

    # 단조성 보장
    q10, q25, q75, q90 = np.sort([q10, q25, q75, q90])

    return [
        {"max": float(q10), "msg": "매우 낮음(하위 10%)"},
        {"min": float(q10), "max": float(q25), "msg": "낮음(하위 25%)"},
        {"min": float(q25), "max": float(q75), "msg": "보통"},
        {"min": float(q75), "max": float(q90), "msg": "높음(상위 25%)"},
        {"min": float(q90), "msg": "매우 높음(상위 10%)"},
    ]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True, help="phase_dataset.csv")
    ap.add_argument("--out", required=True, help="출력 JSON 경로 (예: app/config/2025-10-17_thresholds.json)")
    ap.add_argument("--by", default="phase", choices=["club", "overall", "phase"], help="집계 기준")
    ap.add_argument("--metric", default=",".join(DEFAULT_METRICS), help="사용할 지표 콤마구분")
    ap.add_argument("--phases", default=",".join(DEFAULT_PHASE_KEYS), help="phase 모드에서 사용할 페이즈 목록(콤마구분)")
    args = ap.parse_args()

    df = pd.read_csv(args.csv)
    if df.empty:
        raise ValueError(f'❌ 입력 CSV가 비어 있습니다: {args.csv}')

    metrics = [m.strip() for m in args.metric.split(",") if m.strip()]
    phases  = [p.strip() for p in args.phases.split(",") if p.strip()]

    out_obj = {}

    # overall: 전체 데이터 기반(default 섹션)
    if args.by == "overall":
        out_obj["default"] = {}
        for m in metrics:
            s = _guard_and_clip(df[m], m)
            if len(s) < MIN_SAMPLE:
                print(f"[SKIP] default-{m}: n={len(s)} < {MIN_SAMPLE}")
                continue
            if len(s) > MAX_SAMPLE:
                s = s.tail(MAX_SAMPLE)
            bins = build_bins(s)
            if bins:
                out_obj["default"][m] = {"bins": bins}
            else:
                print(f"[SKIP] default-{m}: degenerate bins")

    # club: 클럽별 평균 기준 (phase 무시)
    elif args.by == "club":
        for club, g in df.groupby("club"):
            club_key = str(club)
            out_obj.setdefault(club_key, {})
            for m in metrics:
                s = _guard_and_clip(g[m], m)
                if len(s) < MIN_SAMPLE:
                    print(f"[SKIP] {club_key}-{m}: n={len(s)} < {MIN_SAMPLE}")
                    continue
                if len(s) > MAX_SAMPLE:
                    s = s.tail(MAX_SAMPLE)
                bins = build_bins(s)
                if bins:
                    out_obj[club_key][m] = {"bins": bins}
                else:
                    print(f"[SKIP] {club_key}-{m}: degenerate bins")

    # phase: 클럽 × 페이즈 기준 (권장)
    else:
        for (club, phase), g in df.groupby(["club", "phase"]):
            if str(phase) not in phases:
                continue
            club_key = str(club)
            out_obj.setdefault(club_key, {})
            for m in metrics:
                s = _guard_and_clip(g[m], m)
                n = len(s)
                if n < MIN_SAMPLE:
                    print(f"[SKIP] {club_key}-{phase}-{m}: n={n} < {MIN_SAMPLE}")
                    continue
                if n > MAX_SAMPLE:
                    s = s.tail(MAX_SAMPLE)
                bins = build_bins(s)
                if bins:
                    out_obj[club_key][f"{phase}.{m}"] = {"bins": bins}
                else:
                    print(f"[SKIP] {club_key}-{phase}-{m}: degenerate bins")

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(out_obj, f, ensure_ascii=False, indent=2)

    print(f"[OK] thresholds -> {out_path}")

if __name__ == "__main__":
    main()