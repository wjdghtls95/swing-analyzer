# app/util/sysload.py
import os
import shutil
import time
from multiprocessing import cpu_count

def ffmpeg_available() -> bool:
    """ffmpeg/ffprobe가 PATH에 있는지 간단히 확인"""
    return shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None

def cpu_load_ratio() -> float:
    """
    1분 load avg / 코어 수 → 간단한 '부하율' 근사치
    - 1.0 ≈ 코어 전체가 풀로드에 가까움
    - 0.5 ≈ 여유 있음
    macOS/Linux에서 동작. Windows는 psutil 권장.
    """
    if hasattr(os, "getloadavg"):
        la1, _, _ = os.getloadavg()
        cores = max(1, cpu_count())
        return la1 / cores
    # Windows 대안 (psutil이 있으면 사용)
    try:
        import psutil
        return psutil.cpu_percent(interval=0.2) / 100.0
    except Exception:
        return 0.0  # 정보를 못 얻으면 여유 있다고 가정

class LoadGate:
    """
    히스테리시스 게이트: 순간 스파이크에 덜 민감하도록 상향/하향 임계선을 둠.
    busy = True  → 부하가 높다 (basic 권장)
    """
    def __init__(self, high: float = 0.9, low: float = 0.6):
        self.high = high
        self.low = low
        self._busy = False
        self._ts = 0.0

    def update(self) -> bool:
        r = cpu_load_ratio()
        now = time.time()
        if not self._busy and r >= self.high:
            self._busy = True
            self._ts = now
        elif self._busy and r <= self.low:
            self._busy = False
            self._ts = now
        return self._busy

# 전역 게이트 인스턴스 (모듈 로드 시 1개)
load_gate = LoadGate(high=0.9, low=0.6)