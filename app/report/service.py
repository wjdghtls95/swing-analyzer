from __future__ import annotations
from typing import Dict, Any, Optional, List
import json

from app.llm.client import get_llm_client


# 간단한 프롬프트 빌더(phase_metrics + diagnosis를 요약)
def _build_prompt(
    phase_metrics: Dict[str, Dict[str, float]],
    diagnosis_by_phase: Dict[str, Dict[str, Any]],
    thresholds_info: Optional[Dict[str, Any]] = None,
    club: Optional[str] = None,
    side: Optional[str] = None,
) -> str:
    # 주요 포인트만 압축
    lines: List[str] = []
    if club:
        lines.append(f"- Club: {club}")
    if side:
        lines.append(f"- Side: {side}")
    lines.append("- Summary: per-phase metrics & diagnosis")

    # 페이즈별 간단 요약
    for ph in sorted(phase_metrics.keys()):
        m = phase_metrics.get(ph) or {}
        d = diagnosis_by_phase.get(ph) or {}
        # 핵심 몇 개만
        elbow = m.get("elbow")
        knee = m.get("knee")
        xt = m.get("x_factor")
        diag_labels = ", ".join([f"{k}:{v}" for k, v in d.items()]) if d else "-"
        lines.append(
            f"  • {ph}: elbow={elbow}, knee={knee}, x_factor={xt} | diag=({diag_labels})"
        )

    # thresholds 간단 표시(있으면)
    if thresholds_info:
        try:
            # 크면 너무 길어지므로 키만
            keys = list(thresholds_info.keys())[:8]
            lines.append(f"- Thresholds sections: {keys}")
        except Exception:
            pass

    return "\n".join(lines)


def build_text_report(
    *,
    phase_metrics: Dict[str, Dict[str, float]],
    diagnosis_by_phase: Dict[str, Dict[str, Any]],
    thresholds: Optional[Dict[str, Any]] = None,
    club: Optional[str] = None,
    side: Optional[str] = None,
    tone: str = "coach",  # coach | neutral 등
    language: str = "ko",  # ko | en
    model: Optional[str] = None,
) -> str:
    """
    간단 LLM 보고서 생성:
      - system: 톤/언어/포맷 지정
      - user: 데이터 요약 전달
    """
    # system 지침(톤/언어/포맷)
    if language == "ko":
        sys = (
            "너는 프로 골프 코치야. 사용자에게 친절하고 간결하게 코칭 노트를 제공해.\n"
            "- 문장 5~8줄 내로 요약\n"
            "- 객관적 지표(elbow/knee/x_factor 등)를 바탕으로 핵심만\n"
            "- 과장 금지, 행동 가능한 팁 2~3개 포함"
        )
    else:
        sys = (
            "You are a professional golf coach. Provide concise, friendly coaching notes.\n"
            "- Keep it within 5–8 sentences\n"
            "- Base comments on objective metrics (elbow/knee/x_factor)\n"
            "- No exaggeration; include 2–3 actionable tips"
        )

    prompt = _build_prompt(
        phase_metrics=phase_metrics,
        diagnosis_by_phase=diagnosis_by_phase,
        thresholds_info=thresholds,
        club=club,
        side=side,
    )

    client = get_llm_client()
    # provider 없으면 자동 Noop → 개발 중에도 바로 확인 가능
    text = client.generate_text(
        user_prompt=prompt,
        system_prompt=sys,
        model=model,
        temperature=0.3,
        max_tokens=500,
        timeout=20.0,
    )
    return text
