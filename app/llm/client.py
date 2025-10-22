# app/llm/client.py
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Literal, Protocol, Optional, Dict, Any
import os
import time

# --- 메시지 타입(간단화) ---
Role = Literal["system", "user", "assistant"]
Message = Dict[str, str]  # {"role": "...", "content": "..."}

class LLMClient(Protocol):
    """Provider-agnostic LLM 인터페이스."""
    def generate(
        self,
        messages: List[Message],
        *,
        model: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: Optional[int] = None,
        timeout: float = 20.0,
    ) -> str: ...

# --- Noop (디폴트/로컬 환경 테스트용) ---
@dataclass
class NoopClient(LLMClient):
    def generate(
        self, messages: List[Message], *, model=None, temperature=0.3, max_tokens=None, timeout=20.0
    ) -> str:
        # 마지막 user 입력을 요약해서 에코해주는 더미
        last_user = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
        return f"[NOOP LLM] received {len(messages)} messages. last_user_snippet={last_user[:120]}"

# --- OpenAI 예시(설치/키 없으면 자동 폴백) ---
@dataclass
class OpenAIClient(LLMClient):
    api_key: str
    default_model: str = "gpt-4o-mini"

    def __post_init__(self):
        try:
            import openai  # type: ignore
            self._openai = openai
            self._openai.api_key = self.api_key
            self._ok = True
        except Exception:
            self._ok = False

    def generate(
        self,
        messages: List[Message],
        *,
        model: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: Optional[int] = None,
        timeout: float = 20.0,
    ) -> str:
        if not self._ok:
            # 설치/키 없으면 Noop으로 폴백
            return NoopClient().generate(messages, model=model, temperature=temperature, max_tokens=max_tokens, timeout=timeout)

        m = model or self.default_model

        # 간단한 재시도(백오프)
        delay = 1.0
        for _ in range(3):
            try:
                # Chat Completions (openai>=1.x 형태 예시)
                from openai import OpenAI  # type: ignore
                client = OpenAI(api_key=self.api_key)
                resp = client.chat.completions.create(
                    model=m,
                    messages=messages,  # [{"role": "...", "content":"..."}]
                    temperature=temperature,
                    max_tokens=max_tokens,
                    timeout=timeout,
                )
                return resp.choices[0].message.content or ""
            except Exception:
                time.sleep(delay)
                delay *= 2
        return "[OpenAIClient ERROR] failed after retries."

# --- 팩토리 ---
def get_llm_client() -> LLMClient:
    provider = os.getenv("LLM_PROVIDER", "noop").lower()
    if provider in ("openai", "oai"):
        key = os.getenv("LLM_API_KEY", "")
        return OpenAIClient(api_key=key)
    return NoopClient()