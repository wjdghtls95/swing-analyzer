# app/analyze/results_builder.py
from __future__ import annotations
from typing import Optional, Dict, Any
from datetime import datetime


def build_result(
    *,
    swing_id: str,
    file_path: str,
    side: str,
    club: Optional[str] = None,
    # 전처리/포즈/페이즈 메타
    used_mode: Optional[str] = None,
    preprocess_ms: Optional[int] = None,
    min_vis: Optional[float] = None,
    phase_method: Optional[str] = None,
    # 탐지 품질
    detected: Optional[int] = None,
    total: Optional[int] = None,
    rate: Optional[float] = None,
    # 결과(선택) — 없으면 응답에서 키 생략
    metrics: Optional[Dict[str, float]] = None,
    phases: Optional[Dict[str, int]] = None,
    phase_metrics: Optional[Dict[str, Dict[str, float]]] = None,
    diagnosis_by_phase: Optional[Dict[str, Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """
    모든 결과 필드를 선택적으로 받아, 값이 있을 때만 포함.
    """
    result: Dict[str, Any] = {
        "swingId": swing_id,
        "input": {
            "filePath": file_path,
            "side": side,
            "club": club,
        },
        "env": "test",  # 필요시 settings.ENV로 대체
        "appVersion": "unknown",  # 필요시 버전화
        "timestamp": _now_ts(),
    }

    # 전처리/포즈/페이즈 메타 블록
    _maybe_put(
        result,
        "preprocess",
        {
            "mode": used_mode,
            "ms": preprocess_ms,
            # 아래 두 값은 settings에서 이미 고정이면 생략 가능
            "fps": 30,
            "height": 720,
            "mirror": False,
        },
    )
    _maybe_put(
        result,
        "pose",
        {
            "frameStep": 3,
            "minVisibility": min_vis,
        },
    )
    _maybe_put(
        result,
        "phase",
        {
            "method": phase_method,
        },
    )

    # 탐지 품질
    _maybe_put(result, "detectedFrames", detected)
    _maybe_put(result, "totalFrames", total)
    _maybe_put(result, "detectionRate", rate)

    # 결과 본문 (값이 있을 때만)
    if metrics:
        _maybe_put(result, "metrics", metrics)
    if phases:
        _maybe_put(result, "phases", phases)
    if phase_metrics:
        _maybe_put(result, "phase_metrics", phase_metrics)
    if diagnosis_by_phase:
        _maybe_put(result, "diagnosis_by_phase", diagnosis_by_phase)

    return result


def _now_ts() -> int:
    # 초 단위 epoch
    return int(datetime.utcnow().timestamp())


def _maybe_put(obj: Dict[str, Any], key: str, value):
    if value is None:
        return
    # 빈 dict는 안 넣고 싶으면 아래 조건 추가:
    # if isinstance(value, dict) and not value:
    #     return
    obj[key] = value
