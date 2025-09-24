"""
왜 확장했나?
- 운영/튜닝에 필요한 품질 지표(detectionRate)와 코칭 다항목 출력(diagnosis)을 위해.
- phases/metrics 필드는 향후 구간 분석/지표 확장(탑/임팩트/척추각/어깨회전 등)을 위한 슬롯.
"""

from enum import Enum
from pydantic import BaseModel
from typing import Optional, Dict, List

class NormMode(str, Enum):
    """
    전처리 선택:
      - basic: 항상 재인코딩(안정/느림) 
      - pro: 하드웨어 인코딩/스마트 카피(빠름) 
      - auto: pro 시도 실패 시 basic fallback
    """
    basic = "basic"
    pro   = "pro"
    auto  = "auto"

class AnalyzeResponse(BaseModel):
    """
    API 응답 모델
    - 필수: swingId, elbowAvgAngle, feedback, landmarkCount
    - 선택: 전처리 메타/품질지표/구간/확장지표/진단
    """
    swingId: str
    elbowAvgAngle: float
    feedback: str
    landmarkCount: int
    preprocessMode: Optional[str] = None
    preprocessMs: Optional[int] = None

    # NEW: 품질/진단/확장 지표
    detectedFrames: Optional[int] = None
    totalFrames: Optional[int] = None
    detectionRate: Optional[float] = None  # 0.0~1.0

    diagnosis: Optional[List[str]] = None
    phases: Optional[Dict[str, Optional[int]]] = None
    metrics: Optional[Dict[str, float]] = None

class UrlRequest(BaseModel):
    """
    URL 입력 분석용 요청 모델
    - norm_mode는 전처리 전략 실험/튜닝에 사용
    """
    s3_url: str
    norm_mode: Optional[NormMode] = NormMode.auto