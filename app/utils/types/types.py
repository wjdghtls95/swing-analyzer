from __future__ import annotations
from typing import TypedDict, Literal, Optional, Dict, Any, List
from pydantic import BaseModel, Field

# LLM 메시지 역할(문자열 리터럴 유니온)
Role = Literal["system", "user", "assistant"]


# 공통 LLM 메시지 스키마
class Message(TypedDict):
    role: Role
    content: str


# LLM 경로/벤더 타입
Transport = Literal["gateway", "compat", "openai", "noop"]
Vendor = Literal["openai", "gemini", "groq", "mistral", "together", "noop"]


# Router Body로 받는 LLM 설정 (평평한 스키마)
class LLMConfig(BaseModel):
    provider: Transport = Field(
        "gateway", description="통신 경로(gateway/compat/openai/noop)"
    )
    vendor: Vendor = Field("openai", description="실제 엔진(openai/gemini/groq/...)")
    model: Optional[str] = Field(None, description="모델명(없으면 서버 기본)")
    api_key: Optional[str] = Field(None, description="가능하면 ENV/시크릿 권장")
    extra: Dict[str, Any] = Field(
        default_factory=dict, description="벤더별 추가 파라미터"
    )
