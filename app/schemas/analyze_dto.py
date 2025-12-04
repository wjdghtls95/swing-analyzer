"""
스윙 분석 API의 Request/Response DTO
Router ↔ Service 간 데이터 전달용
"""
from pydantic import BaseModel, Field
from typing import Optional, Literal

# ============ API Request DTO ============
class AnalyzeSwingRequest(BaseModel):
    """스윙 분석 요청 (FastAPI Router → Service)"""
    file_path: str = Field(..., description="분석할 비디오 파일 경로 (S3 또는 로컬)")
    user_id: str = Field(..., description="사용자 ID")
    club: Literal["driver", "wood", "iron", "wedge", "putter"] = Field(
        default="driver",
        description="사용한 골프 클럽 종류"
    )
    swing_direction: Literal["right", "left"] = Field(
        default="right",
        description="스윙 방향 (우타/좌타)"
    )
    visibility_threshold: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="포즈 keypoint 가시성 임계값 (0.0~1.0)"
    )
    normalize_mode: Literal["height", "shoulder"] = Field(
        default="height",
        description="각도 정규화 모드"
    )

    # LLM 설정 (선택적)
    llm_provider: Optional[str] = Field(default="openai", description="LLM 제공자")
    llm_model: Optional[str] = Field(default="gpt-4o-mini", description="LLM 모델명")

    class Config:
        json_schema_extra = {
            "example": {
                "file_path": "/tmp/swing_video.mp4",
                "user_id": "user_123",
                "club": "driver",
                "swing_direction": "right",
                "visibility_threshold": 0.5,
                "normalize_mode": "height",
                "llm_provider": "openai",
                "llm_model": "gpt-4o-mini"
            }
        }


# ============ API Response DTO ============
class PhaseResult(BaseModel):
    """개별 페이즈 결과"""
    name: str = Field(..., description="페이즈 이름 (Address, Backswing, Top, ...)")
    start_frame: int = Field(..., description="시작 프레임 번호")
    end_frame: int = Field(..., description="종료 프레임 번호")
    timestamp_start: float = Field(..., description="시작 시간(초)")
    timestamp_end: float = Field(..., description="종료 시간(초)")
    key_angles: dict = Field(..., description="주요 각도 측정값 (예: left_elbow=145.2)")


class DiagnosisResult(BaseModel):
    """페이즈별 진단 결과"""
    phase: str = Field(..., description="진단 대상 페이즈")
    score: float = Field(..., ge=0.0, le=100.0, description="점수 (0-100)")
    issues: list[str] = Field(default_factory=list, description="발견된 문제점 목록")
    suggestions: list[str] = Field(default_factory=list, description="개선 제안 목록")


class AnalyzeSwingResponse(BaseModel):
    """스윙 분석 응답 (Service → FastAPI Router)"""
    analysis_id: str = Field(..., description="분석 결과 고유 ID")
    user_id: str
    club: str

    # 페이즈 정보
    phases: list[PhaseResult] = Field(..., description="감지된 6단계 스윙 페이즈")

    # 진단 정보
    diagnosis_by_phase: list[DiagnosisResult] = Field(
        ...,
        description="페이즈별 진단 결과"
    )
    overall_score: float = Field(..., ge=0.0, le=100.0, description="전체 스윙 점수")

    # LLM 피드백
    ai_feedback: str = Field(..., description="AI가 생성한 개선 피드백")

    # 저장 경로 (선택적)
    result_url: Optional[str] = Field(None, description="S3에 저장된 결과 JSON URL")

    class Config:
        json_schema_extra = {
            "example": {
                "analysis_id": "analysis_20240315_123456",
                "user_id": "user_123",
                "club": "driver",
                "phases": [
                    {
                        "name": "Backswing",
                        "start_frame": 10,
                        "end_frame": 45,
                        "timestamp_start": 0.33,
                        "timestamp_end": 1.50,
                        "key_angles": {"left_elbow": 145.2, "right_knee": 125.8}
                    }
                ],
                "diagnosis_by_phase": [
                    {
                        "phase": "Backswing",
                        "score": 72.5,
                        "issues": ["왼쪽 팔꿈치 각도 부족 (145도 < 권장 160도)"],
                        "suggestions": ["어깨 회전을 더 크게 하여 팔꿈치 각도 증가"]
                    }
                ],
                "overall_score": 78.3,
                "ai_feedback": "백스윙 시 상체 회전이 부족합니다...",
                "result_url": "https://s3.../analysis_20240315_123456.json"
            }
        }
