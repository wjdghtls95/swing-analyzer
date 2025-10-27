from __future__ import annotations
from enum import Enum
from app.config.settings import settings


# 스윙 방향
class SideEnum(str, Enum):
    right = "right"
    left = "left"


# 동적 Enum: settings.LLM_PROVIDERS를 Swagger 드롭다운으로 노출
LLMProviderEnum = Enum(
    "LLMProviderEnum",
    {name.upper().replace("-", "_"): name for name in settings.LLM_PROVIDERS},
)
