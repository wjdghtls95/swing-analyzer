# tests/test_angle.py
import numpy as np
from app.analyze.angle import calculate_elbow_angle, calculate_knee_angle


def _empty_frame():
    """MediaPipe 33개 랜드마크 기본 프레임(가시성 1.0)"""
    return [{"x": 0.0, "y": 0.0, "z": 0.0, "visibility": 1.0} for _ in range(33)]


def test_elbow_angle_visibility_filter():
    """
    visibility < min_vis 인 프레임은 스킵되는지 확인.
    첫 프레임은 elbow visibility=0.1 (스킵), 두 번째 프레임만 유효.
    """
    frames = []

    f1 = _empty_frame()
    # 우측 팔: 12-14-16 (shoulder-elbow-wrist)
    f1[14]["visibility"] = 0.1  # 스킵 대상
    frames.append(f1)

    f2 = _empty_frame()
    # 간단히 수평-수직 직각(90도)이 나오도록 배치
    # shoulder(12)=(0,0,0), elbow(14)=(1,0,0), wrist(16)=(1,1,0) → 90도
    f2[12].update({"x": 0.0, "y": 0.0, "z": 0.0})
    f2[14].update({"x": 1.0, "y": 0.0, "z": 0.0})
    f2[16].update({"x": 1.0, "y": 1.0, "z": 0.0})
    frames.append(f2)

    angle = calculate_elbow_angle(frames, side="right", min_vis=0.5)
    # 한 프레임만 유효하므로 90±(수치 오차)
    assert not np.isnan(angle)
    assert 85.0 <= angle <= 95.0


def test_knee_angle_basic():
    """
    무릎 각도 계산이 NaN이 아닌지 확인(간단 배치).
    오른쪽 다리: 24-26-28 (hip-knee-ankle)
    """
    frames = []
    f = _empty_frame()
    # 직선에 가깝게 배치 → 각도 ~180도 근처
    f[24].update({"x": 0.0, "y": 0.0, "z": 0.0})
    f[26].update({"x": 1.0, "y": 0.0, "z": 0.0})
    f[28].update({"x": 2.0, "y": 0.0, "z": 0.0})
    frames.append(f)

    angle = calculate_knee_angle(frames, side="right", min_vis=0.5)
    assert not np.isnan(angle)
    assert 160.0 <= angle <= 180.0
