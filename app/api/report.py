# app/api/report.py
from __future__ import annotations
from typing import Optional, Dict, Any
from fastapi import APIRouter, Body, Query

from app.report.service import build_text_report
from app.utils.resource_finder import rf  # thresholds_path() 쓸 수 있으면 사용
import json
from pathlib import Path

router = APIRouter()


@router.post("/report", tags=["Report"])
def build_report_api(
    payload: Dict[str, Any] = Body(
        ...,
        description="analyze_swing 결과 중 일부(phase_metrics, diagnosis_by_phase 등)",
    ),
    language: str = Query("ko", regex="^(ko|en)$"),
    tone: str = Query("coach"),
    model: Optional[str] = Query(None),
):
    # 입력에서 필요한 것만 추출(프론트가 analyze_swing 결과를 그대로 보내준다는 가정)
    phase_metrics = payload.get("phase_metrics") or {}
    diagnosis_by_phase = payload.get("diagnosis_by_phase") or {}
    club = (payload.get("input") or {}).get("club") or payload.get("club")
    side = payload.get("side") or (payload.get("input") or {}).get("side")

    # thresholds는 파일에서 읽거나, 프론트가 같이 보내줄 수도 있음
    thresholds = payload.get("thresholds")
    if thresholds is None:
        p = rf.thresholds_path()
        if p and Path(p).exists():
            thresholds = json.loads(Path(p).read_text(encoding="utf-8"))

    text = build_text_report(
        phase_metrics=phase_metrics,
        diagnosis_by_phase=diagnosis_by_phase,
        thresholds=thresholds,
        club=club,
        side=side,
        tone=tone,
        language=language,
        model=model,
    )
    return {"report": text}
