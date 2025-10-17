from __future__ import annotations
from typing import Dict, Any, Optional, List


def _classify_value(v: float, bins: List[dict]) -> Optional[str]:
    """
    bins: [{"max":..., "msg":"..."}, {"min":..., "max":..., "msg":"..."}, {"min":..., "msg":"..."}]
    min 없으면 -inf, max 없으면 +inf 로 간주. 경계 포함은 mn <= v <= mx
    """
    if v is None or bins is None:
        return None
    for b in bins:
        mn = b.get("min", float("-inf"))
        mx = b.get("max", float("inf"))
        if mn <= v <= mx:
            return b.get("msg")
    return None


def _pick_bins(thresholds: Dict[str, Any], club_key: str, phase_key: str, metric: str):
    """
    우선순위 없음(심플): 클럽 섹션에서 "P?.metric" 키만 본다.
    예) thresholds["iron"]["P4.elbow"]["bins"]
    """
    club_map = thresholds.get(club_key, {}) if club_key else {}
    key = f"{phase_key}.{metric}"
    spec = club_map.get(key)
    if isinstance(spec, dict):
        bins = spec.get("bins")
        return bins if isinstance(bins, list) else None
    return None


def build_phase_diagnosis(
    phase_metrics: Dict[str, Dict[str, float]],
    club: Optional[str],
    thresholds: Dict[str, Any],
    metrics: List[str],
) -> Dict[str, Any]:
    """
    입력:
      phase_metrics: {"P2": {"elbow": 120.1, "knee": ...}, "P3": {...}, ...}
      club: "iron" | "driver"
      thresholds: app/config/thresholds.json 로드한 dict
      metrics: 라벨링 대상 메트릭 목록 (예: ["elbow","knee","spine_tilt","shoulder_turn","hip_turn","x_factor"])

    출력:
      {"P2": {"elbow_diag": "적정(25~75%)", ...}, "P3": {...}, ...}
    """
    out: Dict[str, Any] = {}
    club_key = str(club or "")
    for ph, mvals in phase_metrics.items():
        row = {}
        for m in metrics:
            if m not in mvals:
                continue
            bins = _pick_bins(thresholds, club_key, ph, m)
            if not bins:
                continue  # bins 없으면 그 항목은 생성 안함
            label = _classify_value(mvals[m], bins)
            if label:
                row[f"{m}_diag"] = label
        if row:
            out[ph] = row
    return out