import os
import time
import hashlib
import json as _json
from typing import Optional, Dict, Any

from app.config.settings import settings
from app.analyze.schema import ClubType


# ----- Meta helpers -----

def app_version() -> str:
    """앱/이미지 버전 문자열 반환 (settings > ENV > 'unknown')."""
    try:
        return (
            getattr(settings, "APP_VERSION", None)
            or os.environ.get("APP_VERSION")
            or "unknown"
        )
    except Exception:
        return "unknown"


def rules_fingerprint(rules: dict) -> str:
    """thresholds 룰 dict의 고유 식별자(fingerprint) → sha1 해시 앞 10자리."""
    if not isinstance(rules, dict):
        return "no-rules"
    try:
        payload = _json.dumps(rules, sort_keys=True, ensure_ascii=False).encode("utf-8")
        return hashlib.sha1(payload).hexdigest()[:10]
    except Exception:
        return "hash-error"


# ----- 작은 조각 빌더들 -----
def build_input_meta(file_path: str, side: str, club: Optional[ClubType]) -> Dict[str, Any]:
    """입력 관련 메타데이터 블록 (경로, side, 클럽)."""
    return {
        "filePath": file_path,
        "side": side,
        "club": club.value if club else None,
    }


def build_preprocess_meta(used_mode: str, preprocess_ms: int) -> Dict[str, Any]:
    """전처리 단계 메타데이터 (mode, 시간, fps, height, mirror)."""
    return {
        "mode": used_mode,  # "pro" | "basic"
        "ms": preprocess_ms,
        "fps": getattr(settings, "VIDEO_FPS", None),
        "height": getattr(settings, "VIDEO_HEIGHT", None),
        "mirror": getattr(settings, "VIDEO_MIRROR", None),
    }


def build_pose_meta(min_vis: float) -> Dict[str, Any]:
    """포즈 추출 설정 메타데이터 (frameStep, minVisibility)."""
    return {
        "frameStep": getattr(settings, "POSE_FRAME_STEP", 3),
        "minVisibility": min_vis,
    }


def build_rules_meta(rules: dict, club: Optional[ClubType]) -> Dict[str, Any]:
    """사용된 thresholds 룰셋 메타데이터 (클럽, fingerprint, keyCount)."""
    return {
        "club": club.value if club else None,
        "fingerprint": rules_fingerprint(rules),
        "keyCount": len(rules) if isinstance(rules, dict) else 0,
    }


def build_phase_meta(method: str) -> Dict[str, Any]:
    """phase 검출 방식 기록 (auto | rule | ml)."""
    return {"method": method}


# ----- 최종 결과 빌더 -----

def build_result(
    *,
    swing_id: str,
    file_path: str,
    side: str,
    club: Optional[ClubType],
    used_mode: str,
    preprocess_ms: int,
    min_vis: float,
    phase_method: str,
    detected: int,
    total: int,
    rate: Optional[float],
    metrics: Dict[str, Any],
    phases: Dict[str, Any],
    phase_metrics: Dict[str, Any],
    diagnosis_by_phase: Dict[str, Any],
    rules: dict,
) -> Dict[str, Any]:
    """서비스 계산 결과들을 합쳐 최종 응답/로그 JSON 생성."""
    return {
        "swingId": swing_id,

        # inputs / context
        "input": build_input_meta(file_path, side, club),
        "env": getattr(settings, "ENV", None),
        "appVersion": app_version(),
        "timestamp": int(time.time()),

        # meta blocks
        "preprocess": build_preprocess_meta(used_mode, preprocess_ms),
        "pose": build_pose_meta(min_vis),
        "rules": build_rules_meta(rules, club),
        "phase": build_phase_meta(phase_method),

        # core outputs
        "detectedFrames": detected,
        "totalFrames": total,
        "detectionRate": rate,

        "metrics": metrics,
        "phases": phases,
        "phase_metrics": phase_metrics,
        "diagnosis_by_phase": diagnosis_by_phase,
    }