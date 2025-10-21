from typing import Dict, Any, Optional
from .jsonio import safe_get


def flatten_phase_metrics(
    pm: Optional[Dict[str, Dict[str, float]]],
) -> Dict[str, float]:
    flat = {}
    for ph, vals in (pm or {}).items():
        if isinstance(vals, dict):
            for k, v in vals.items():
                flat[f"phase.{ph}.{k}"] = v
    return flat


def flatten_diag_by_phase(diag: Optional[Dict[str, Dict[str, str]]]) -> Dict[str, str]:
    out = {}
    for ph, vals in (diag or {}).items():
        if isinstance(vals, dict):
            for k, v in vals.items():
                out[f"diag.{ph}.{k}"] = v
    return out


def flatten_core_blocks(d: Dict[str, Any]) -> Dict[str, Any]:
    base = {
        "swingId": d.get("swingId"),
        "input.filePath": safe_get(d, "input.filePath"),
        "input.side": safe_get(d, "input.side"),
        "input.club": safe_get(d, "input.club"),
        "env": d.get("env"),
        "appVersion": d.get("appVersion"),
        "timestamp": d.get("timestamp"),
        "preprocess.mode": safe_get(d, "preprocess.mode"),
        "preprocess.ms": safe_get(d, "preprocess.ms"),
        "preprocess.fps": safe_get(d, "preprocess.fps"),
        "preprocess.height": safe_get(d, "preprocess.height"),
        "preprocess.mirror": safe_get(d, "preprocess.mirror"),
        "pose.frameStep": safe_get(d, "pose.frameStep"),
        "pose.minVisibility": safe_get(d, "pose.minVisibility"),
        "rules.club": safe_get(d, "rules.club"),
        "rules.fingerprint": safe_get(d, "rules.fingerprint"),
        "rules.keyCount": safe_get(d, "rules.keyCount"),
        "phase.method": safe_get(d, "phase.method"),
        "detectedFrames": d.get("detectedFrames"),
        "totalFrames": d.get("totalFrames"),
        "detectionRate": d.get("detectionRate"),
    }
    # metrics
    for k, v in (d.get("metrics") or {}).items():
        base[f"metrics.{k}"] = v
    # phase idx
    for k, v in (d.get("phases") or {}).items():
        base[f"phase_idx.{k}"] = v
    return base
