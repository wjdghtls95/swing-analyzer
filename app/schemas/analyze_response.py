from pydantic import BaseModel, Field
from typing import List, Optional, Dict


class PhaseResultDto(BaseModel):
    """페이즈별 결과"""
    name: str = Field(..., description="페이즈 이름")
    start_frame: int
    end_frame: int
    timestamp_start: float
    timestamp_end: float
    key_angles: Dict[str, float] = Field(
        ...,
        description="대표 각도 (예: shoulder_angle, hip_angle)"
    )


class DiagnosisResultDto(BaseModel):
    """페이즈별 진단 결과"""
    phase: str
    score: int = Field(..., ge=0, le=100)
    issues: List[str]
    suggestions: List[str]


class AnalyzeSwingApiResponse(BaseModel):
    """스윙 분석 API 응답 DTO"""

    analysis_id: str = Field(..., description="분석 고유 ID")
    user_id: str
    club: str

    # 6개 페이즈별 결과
    phases: List[PhaseResultDto] = Field(
        ...,
        min_items=6,
        max_items=6,
        description="Address, Backswing, Top, Downswing, Impact, Follow-through"
    )

    # 6개 페이즈별 진단
    diagnosis_by_phase: List[DiagnosisResultDto] = Field(
        ...,
        min_items=6,
        max_items=6
    )

    overall_score: int = Field(..., ge=0, le=100, description="전체 점수")
    ai_feedback: Optional[str] = Field(None, description="LLM 생성 피드백")
    result_url: Optional[str] = Field(None, description="S3 저장 URL")

    # 메타데이터
    api_version: str = Field(default="2.0.0")
    processing_time_ms: int = Field(..., description="처리 시간 (밀리초)")

    class Config:
        json_schema_extra = {
            "example": {
                "analysis_id": "a1b2c3d4-e5f6-7890",
                "user_id": "user123",
                "club": "driver",
                "phases": [
                    {
                        "name": "Address",
                        "start_frame": 0,
                        "end_frame": 30,
                        "timestamp_start": 0.0,
                        "timestamp_end": 1.0,
                        "key_angles": {
                            "shoulder_angle": 45.2,
                            "hip_angle": 30.1,
                            "knee_angle": 135.4
                        }
                    }
                    # ... 5개 페이즈 더
                ],
                "diagnosis_by_phase": [
                    {
                        "phase": "Address",
                        "score": 85,
                        "issues": ["어깨가 약간 올라가 있습니다"],
                        "suggestions": ["어깨를 자연스럽게 내리세요"]
                    }
                    # ... 5개 페이즈 더
                ],
                "overall_score": 78,
                "ai_feedback": "전반적으로 좋은 스윙입니다...",
                "result_url": "https://s3.../analysis.json",
                "api_version": "2.0.0",
                "processing_time_ms": 12500
            }
        }