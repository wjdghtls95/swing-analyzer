# tests/test_thresholds.py
import importlib
import types

def test_diagnosis_from_thresholds(monkeypatch):
    """
    metrics → thresholds bins 매칭으로 elbow/knee 진단이 생성되는지 확인.
    thresholds.json 유무와 무관하게, 서비스 내부 _THRESH를 임시로 교체해 검증.
    """
    from app.analyze import service as svc

    # 가짜 thresholds 사양 주입
    fake_thresh = {
        "elbow_avg": {
            "bins": [
                {"max": 120, "msg": "팔꿈치 굴곡이 큰 편입니다."},
                {"min": 120, "max": 999, "msg": "팔꿈치 각도가 적정 범위입니다."}
            ]
        },
        "knee_avg": {
            "bins": [
                {"max": 140, "msg": "무릎 굴곡이 큰 편입니다."},
                {"min": 140, "max": 999, "msg": "무릎 각도가 적정 범위입니다."}
            ]
        }
    }
    monkeypatch.setattr(svc, "_THRESH", fake_thresh, raising=True)

    metrics = {"elbow_avg": 110.0, "knee_avg": 128.0}
    out = svc._apply_bins_metrics_dict(metrics)

    assert out.get("elbow_diag") == "팔꿈치 굴곡이 큰 편입니다."
    assert out.get("knee_diag") == "무릎 굴곡이 큰 편입니다."