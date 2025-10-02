from typing import Dict, Any, Optional, TypedDict, Literal

PhaseMethod = Literal["auto", "ml", "rule"]

class FlatRow(TypedDict, total=False):
    file: str
    swingId: Optional[str]
    env: Optional[str]
    appVersion: Optional[str]
    timestamp: Optional[int]
    detectionRate: Optional[float]
    # ... 필요 필드들 확장

PHASE_KEYS = [f"P{i}" for i in range(2, 10)]