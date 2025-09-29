from app.analyze.angle import angles_at_frame

def test_angles_at_frame_nan_safe():
    # 비어있는 프레임일 때도 예외 없이 NaN/빈값 처리
    out = angles_at_frame([], side="right")
    assert set(out.keys()) == {"elbow", "knee", "spine_tilt"}