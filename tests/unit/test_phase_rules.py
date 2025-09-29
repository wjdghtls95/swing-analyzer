import math
from app.analyze.service import _apply_bins_metrics_dict

def test_phase_level_rules():
    rules = {
        "P4.elbow": {"bins": [
            {"max": 110, "msg": "Low"},
            {"min": 110, "max": 145, "msg": "OK"},
            {"min": 145, "msg": "High"}
        ]},
        "P7.knee": {"bins": [
            {"max": 130, "msg": "Deep"},
            {"min": 130, "max": 165, "msg": "OK"},
            {"min": 165, "msg": "Extended"}
        ]}
    }
    metrics = {"P4.elbow": 120.0, "P7.knee": 170.0}
    out = _apply_bins_metrics_dict(metrics, rules)
    assert out["P4_elbow_diag"] == "OK"
    assert out["P7_knee_diag"] == "Extended"