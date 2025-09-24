"""
왜 분리했나?
- 수학/기하(각도 계산) 로직을 분석/피드백에서 분리하면 테스트/재사용이 쉬움(Separation of Concerns).
- elbow 뿐 아니라 무릎, 척추 등 모든 관절 각도에 공통 패턴을 재사용 가능.
"""

import numpy as np
from typing import List, Dict

# MediaPipe Pose 인덱스 (오른팔/왼팔)
_RIGHT = (12, 14, 16)  # shoulder, elbow, wrist (right)
_LEFT  = (11, 13, 15)  # shoulder, elbow, wrist (left)

# MediaPipe Pose 인덱스 (오른 무릎/왼무릎)
_KNEE_RIGHT = (24, 26, 28)
_KNEE_LEFT  = (23, 25, 27)

def _angle_deg(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> float:
    """
    벡터 끼인각 ∠ABC(도 단위)를 구한다.
    - 수치 안정성을 위해 코사인 값을 -1~1로 clamp.
    - BA = A - B, BC = C - B, cosθ = (BA·BC)/(|BA||BC|)
    """
    ba = a - b
    bc = c - b
    nba = np.linalg.norm(ba); nbc = np.linalg.norm(bc)
    if nba == 0.0 or nbc == 0.0:  # 두 점이 같으면 각도 계산 불가
        return np.nan
    cosv = float(np.dot(ba, bc) / (nba * nbc))
    cosv = max(-1.0, min(1.0, cosv))
    return float(np.degrees(np.arccos(cosv)))

def _xyz(lm: Dict[str, float]) -> np.ndarray:
    """
    Mediapipe landmark dict → np.array([x,y,z]) 변환.
    - 좌표는 정규화(0~1). z는 상대 깊이. 2D만 써도 동작 가능.
    """
    return np.array([lm.get("x", 0.0), lm.get("y", 0.0), lm.get("z", 0.0)], dtype=float)

def calculate_elbow_angle(
    landmarks: List[List[Dict[str, float]]],
    side: str = "right",
    min_vis: float = 0.5
) -> float:
    """
    프레임별 팔꿈치 각도를 계산하고, 유효 프레임들 평균(소수 1자리)을 반환.
    - side: 'right' or 'left' (손잡이/카메라 세팅에 맞춰 선택)
    - min_vis: 세 관절 중 하나라도 visibility < min_vis이면 해당 프레임 제외(잡음 제거)
    - 유효 프레임이 없으면 NaN 반환 → 상위 레이어에서 친절 메시지 처리
    """
    idxs = _RIGHT if side.lower() == "right" else _LEFT
    angles: List[float] = []

    for frame in landmarks:
        if not frame or len(frame) < max(idxs) + 1:
            continue  # 관절 갯수가 부족하면 스킵
        s, e, w = frame[idxs[0]], frame[idxs[1]], frame[idxs[2]]
        # 가시성 필터: 품질이 낮은 프레임 제외(분모=0, NaN 방지)
        if any(lm.get("visibility", 1.0) < min_vis for lm in (s, e, w)):
            continue
        ang = _angle_deg(_xyz(s), _xyz(e), _xyz(w))
        if not np.isnan(ang) and np.isfinite(ang):
            angles.append(ang)

    if not angles:
        return float("nan")

    return float(np.round(np.mean(angles), 1))

def calculate_knee_angle(
    landmarks: List[List[Dict[str, float]]],
    side: str = "right",
    min_vis: float = 0.5
) -> float:
    """
    평균 무릎 각도(hip–knee–ankle)를 계산해 반환.
    - 페이즈 무관 전체 평균. 나중에 P7(임팩트) 각도로 확장 가능.
    """
    idxs = _KNEE_RIGHT if side.lower() == "right" else _KNEE_LEFT
    angles: List[float] = []
    for frame in landmarks:
        if not frame or len(frame) < max(idxs) + 1:
            continue
        h, k, a = frame[idxs[0]], frame[idxs[1]], frame[idxs[2]]
        if any(lm.get("visibility", 1.0) < min_vis for lm in (h, k, a)):
            continue
        ang = _angle_deg(_xyz(h), _xyz(k), _xyz(a))
        if not np.isnan(ang) and np.isfinite(ang):
            angles.append(ang)

    return float(np.round(np.mean(angles), 1)) if angles else float("nan")