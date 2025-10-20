"""
왜 분리했나?
- 수학/기하(각도 계산) 로직을 분석/피드백(service)에서 분리하면 테스트/재사용이 쉬움.
- 팔꿈치/무릎/척추 등 모든 관절 각도 계산에 공통 패턴을 적용.
"""
from typing import List, Dict, Sequence, Tuple, Optional
import math
import numpy as np

# MediaPipe 인덱스/트리플릿은 하드코딩하지 않고 constants에서 가져온다
from app.analyze.constants import (
    L_SHOULDER, R_SHOULDER, L_ELBOW, R_ELBOW, L_WRIST, R_WRIST,
    L_HIP, R_HIP, L_KNEE, R_KNEE, L_ANKLE, R_ANKLE,
    RIGHT_ARM, LEFT_ARM, RIGHT_LEG, LEFT_LEG,
)

def calculate_elbow_angle(
    landmarks: List[List[Dict[str, float]]],
    side: str = "right",
    min_vis: float = 0.5,
) -> float:
    """
    프레임 시퀀스에서 팔꿈치(어깨-팔꿈치-손목) 각도의 평균(소수 1자리)을 반환.
    - side: 'right' 또는 'left'
    - min_vis: 세 관절 중 하나라도 visibility < min_vis면 해당 프레임 제외
    - 유효 프레임이 없으면 NaN 반환
    """
    triplet = RIGHT_ARM if side.lower() == "right" else LEFT_ARM
    return _sequence_mean_angle(landmarks, triplet, min_vis=min_vis)


def calculate_knee_angle(
    landmarks: List[List[Dict[str, float]]],
    side: str = "right",
    min_vis: float = 0.5,
) -> float:
    """
    프레임 시퀀스에서 무릎(엉덩이-무릎-발목) 각도의 평균(소수 1자리)을 반환.
    - side: 'right' 또는 'left'
    - min_vis: 세 관절 중 하나라도 visibility < min_vis면 해당 프레임 제외
    - 유효 프레임이 없으면 NaN 반환
    """
    triplet = RIGHT_LEG if side.lower() == "right" else LEFT_LEG
    return _sequence_mean_angle(landmarks, triplet, min_vis=min_vis)

def angles_at_frame(
    frame_landmarks: Sequence[Dict[str, float]],
    side: str = "right",
    min_vis: float = 0.0,
) -> Dict[str, float]:
    """
    단일 프레임에서 주요 각도를 계산해 반환.
    반환 키: {'elbow': float|NaN, 'knee': float|NaN, 'spine_tilt': float|NaN}

    - elbow: (어깨-팔꿈치-손목) 꺾임각
    - knee:  (엉덩이-무릎-발목) 꺾임각
    - spine_tilt: 어깨중점→엉덩이중점 선의 화면상 기울기.
        * 계산: atan2(vy, vx) [수평 기준 각도] → 수직 기준으로 변환: abs(90 - abs(deg))
        * 좌표계(y가 아래로 증가) 가정하에 직관적 지표로 사용
    """
    # ---- 팔/다리 트리플릿 선택
    arm = RIGHT_ARM if side.lower() == "right" else LEFT_ARM
    leg = RIGHT_LEG if side.lower() == "right" else LEFT_LEG

    # ---- 팔꿈치 각도
    elbow = _angle_from_triplet(frame_landmarks, arm, min_vis=min_vis)

    # ---- 무릎 각도
    knee = _angle_from_triplet(frame_landmarks, leg, min_vis=min_vis)

    # ---- 척추 기울기 (어깨/엉덩이의 중점 벡터)
    spine_tilt = float("nan")
    try:
        rs = frame_landmarks[R_SHOULDER]
        ls = frame_landmarks[L_SHOULDER]
        rh = frame_landmarks[R_HIP]
        lh = frame_landmarks[L_HIP]


        if all(lm.get("visibility", 1.0) >= min_vis for lm in (rs, ls, rh, lh)):
            mid_sh = ((_get(rs, "x") + _get(ls, "x")) / 2.0,
                      (_get(rs, "y") + _get(ls, "y")) / 2.0)

            mid_hip = ((_get(rh, "x") + _get(lh, "x")) / 2.0,
                       (_get(rh, "y") + _get(lh, "y")) / 2.0)

            vx, vy = (mid_hip[0] - mid_sh[0], mid_hip[1] - mid_sh[1])

            deg_h = math.degrees(math.atan2(vy, vx))          # 수평기준

            spine_tilt = abs(90.0 - abs(deg_h))               # 수직기준 절대 기울기
            spine_tilt = float(np.round(spine_tilt, 1))
    except Exception:
        spine_tilt = float("nan")

    # ── 추가: 어깨/엉덩이 회전 각도 + X-팩터 ─────────────────
    shoulder_turn = float("nan")
    hip_turn = float("nan")
    x_factor = float("nan")

    try:
        rs = frame_landmarks[R_SHOULDER]
        ls = frame_landmarks[L_SHOULDER]
        rh = frame_landmarks[R_HIP]
        lh = frame_landmarks[L_HIP]

        if all(lm.get("visibility", 1.0) >= min_vis for lm in (ls, rs)):
            shoulder_turn = _line_angle(ls, rs)  # 왼→오른 어깨 라인 각도
        if all(lm.get("visibility", 1.0) >= min_vis for lm in (lh, rh)):
            hip_turn = _line_angle(lh, rh)  # 왼→오른 엉덩이 라인 각도

        shoulder_turn = _wrap_deg(shoulder_turn)
        hip_turn = _wrap_deg(hip_turn)

        # X-팩터 계산: 어깨 - 엉덩이 (부호 있는 최소차, [-180, 180]로 래핑)
        x_factor = _delta_deg(shoulder_turn, hip_turn)

        # 도메인 안정화를 위해 클램프(권장 범위: [-60, 60])
        x_factor = _clamp(x_factor, -60.0, 60.0)
    except Exception:
        x_factor = float('nan')

    # 기존 반환 dict에 합치기
    base = {
        "elbow": float(np.round(elbow, 1)) if np.isfinite(elbow) else float("nan"),
        "knee": float(np.round(knee, 1)) if np.isfinite(knee) else float("nan"),
        "spine_tilt": spine_tilt,
        "shoulder_turn": float(np.round(shoulder_turn, 1)) if math.isfinite(shoulder_turn) else float("nan"),
        "hip_turn": float(np.round(hip_turn, 1)) if math.isfinite(hip_turn) else float("nan"),
        "x_factor": float(np.round(x_factor, 1)) if math.isfinite(x_factor) else float("nan"),
    }

    return base

# Internal utils
# 내부 유틸 (모듈 외부로 공개하지 않음)
def _sequence_mean_angle(
    sequence: List[List[Dict[str, float]]],
    triplet: Tuple[int, int, int],
    min_vis: float = 0.5,
) -> float:
    """
    프레임 시퀀스와 (A,B,C) 인덱스(triplet)를 받아
    각 프레임의 ∠ABC를 계산하고 유효 프레임 평균을 반환(소수 1자리).
    """
    if not sequence:
        return float("nan")

    vals: List[float] = []
    for frame in sequence:
        ang = _angle_from_triplet(frame, triplet, min_vis=min_vis)
        if np.isfinite(ang):
            vals.append(ang)

    if not vals:
        return float("nan")
    return float(np.round(np.mean(vals), 1))


def _angle_from_triplet(
    frame: Sequence[Dict[str, float]],
    triplet: Tuple[int, int, int],
    min_vis: float = 0.0,
) -> float:
    """
    단일 프레임에서 (A,B,C) 인덱스의 끼인각 ∠ABC를 계산.
    visibility < min_vis가 하나라도 있으면 NaN.
    """
    a_idx, b_idx, c_idx = triplet
    # 인덱스 범위/데이터 유효성
    if max(triplet) >= len(frame):
        return float("nan")

    a, b, c = frame[a_idx], frame[b_idx], frame[c_idx]

    # visibility 체크(키 없으면 1.0으로 간주)
    for lm in (a, b, c):
        if lm.get("visibility", 1.0) < min_vis:
            return float("nan")

    A = _xyz(a); B = _xyz(b); C = _xyz(c)
    return _angle_deg(A, B, C)


def _angle_deg(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> float:
    """
    벡터 끼인각 ∠ABC(도 단위).
    BA = A - B, BC = C - B
    cosθ = (BA·BC)/(|BA||BC|), 수치 안정성을 위해 clamp.
    """
    ba = a - b
    bc = c - b
    nba = float(np.linalg.norm(ba))
    nbc = float(np.linalg.norm(bc))
    if nba == 0.0 or nbc == 0.0:
        return float("nan")
    cosv = float(np.dot(ba, bc) / (nba * nbc))
    cosv = max(-1.0, min(1.0, cosv))
    return float(np.degrees(np.arccos(cosv)))


def _xyz(lm: Dict[str, float]) -> np.ndarray:
    """
    Mediapipe landmark dict → np.array([x, y, z]) 변환.
    - 좌표는 정규화(0~1). z는 상대 깊이(없으면 0).
    """
    return np.array([
        _get(lm, "x"),
        _get(lm, "y"),
        _get(lm, "z"),
    ], dtype=float)


def _get(lm: Dict[str, float], k: str, default: float = 0.0) -> float:
    """
    dict 안전 접근. 키 없으면 default.
    """
    v = lm.get(k, default)
    try:
        return float(v)
    except Exception:
        return default

# 좌우 두 점으로 라인 각도(수평 = 0°, 시계방향 양수)
def _line_angle(p_left, p_right):
    try:
        dx = _get(p_right, "x") - _get(p_left, "x")
        dy = _get(p_right, "y") - _get(p_left, "y")
        # 화면 좌표(y 아래로 증가) 고려해서 -dy
        return math.degrees(math.atan2(-dy, dx))
    except Exception:
        return float("nan")

# 각도 정규화 유틸
def _wrap_deg(a: float) -> float:
    """임의의 각도를 [-180, 180]로 래핑"""
    if not math.isfinite(a):
        return float("nan")
    a = (a + 180.0) % 360.0 - 180.0
    if a == -180.0:
        a = 180.0
    return a

def _delta_deg(a: float, b: float) -> float:
    """두 각도의 최소 부호 있는 차이( a - b ), 결과 [-180, 180]"""
    if not (math.isfinite(a) and math.isfinite(b)):
        return float("nan")
    d = (a - b + 180.0) % 360.0 - 180.0
    if d == -180.0:
        d = 180.0
    return d


def _clamp(v: float, lo: float, hi: float) -> float:
    """간단 클램프(LLM/후처리를 위한 안정화)"""
    if not math.isfinite(v):
        return v
    return max(lo, min(hi, v))