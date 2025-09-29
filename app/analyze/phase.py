"""
Phase 구간 계산 모듈
- Mediapipe landmarks 시퀀스를 받아 주요 phase (P2~P9) 프레임 인덱스를 잡아냄
- 현재는 naive rule (단순 분할 or landmark peak) 기반
- 나중에 ML/heuristic 개선 가능
"""

from typing import Dict, List, Any

def detect_phases(landmarks: List[List[Dict[str, Any]]]) -> Dict[str, int]:
    """
    landmarks: 프레임별 포즈 랜드마크 리스트
    return: {"P2": idx, "P3": idx, ..., "P9": idx}
    """
    total = len(landmarks)
    if total < 9:
        # 최소 프레임이 부족하면 분할 불가 → None 반환
        return {f"P{i}": None for i in range(2, 10)}

    # 현재는 단순 equal-split (데모 목적)
    step = total // 8
    phases = {f"P{i}": step * (i - 2) for i in range(2, 10)}
    return phases