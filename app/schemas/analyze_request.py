from pydantic import BaseModel, Field, validator
from typing import Optional, Literal

class AnalyzeSwingApiRequest(BaseModel):
    """스윙 분석 API Request (Form 데이터 구조화)"""
    user_id: Optional[str] = Field(
        default=None,
        description="사용자 ID (개인화 기능에 필요할 때 사용)"
    )

    # 클럽 종류 (driver/iron/wedge)
    club: Literal["driver", "iron", "wedge"] = Field(
        ...,
        description="클럽 종류"
    )

    # 스윙 방향을 도메인과 동일하게 right/left로 제한
    swing_direction: Literal["right", "left"] = Field(
        default="right",
        description="스윙 방향 (우타/좌타)"
    )

    # 포즈 가시성 임계값
    visibility_threshold: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="MediaPipe 포즈 가시성 임계값"
    )

    # 각도 정규화 모드: height/shoulder만 허용
    normalize_mode: Literal["height", "shoulder"] = Field(
        default="height",
        description="각도 정규화 모드 (height: 키 기준, shoulder: 어깨 기준)"
    )

    # LLM 제공자
    llm_provider: Optional[Literal['noop', "openai", "anthropic"]] = Field(
        default=None,
        description="LLM 제공자 (noop: 테스트 모드, openai: OpenAI API, anthropic: Claude API)"
    )

    # LLM 모델app/schemas/video_dto.py:7:20
    llm_model: Optional[str] = Field(
        default=None,
        description="LLM 모델명 (예: gpt-4o-mini)"
    )

    @validator("llm_model")
    def validate_llm_model(cls, v, values):
        """llm_provider가 openai/anthropic면 llm_model도 필수"""
        provider = values.get("llm_provider")
        if provider and provider != "noop" and not v:
            raise ValueError("llm_provider가 openai/anthropic이면 llm_model도 필수입니다")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user123",
                "club": "driver",
                "swing_direction": "right",
                "visibility_threshold": 0.5,
                "normalize_mode": "height",
                "llm_provider": "noop or openai",
                "llm_model": "gpt-4o-mini"
            }
        }
