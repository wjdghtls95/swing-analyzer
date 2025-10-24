# app/llm/client.py
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Literal, Protocol, Optional, Dict
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

    # 편의 함수: system/user만 받아 간단 호출
    def generate_text(
        self,
        user_prompt: str,
        *,
        system_prompt: str = "You are a helpful assistant.",
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
        last_user = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
        return f"[NOOP LLM] messages={len(messages)}; last_user_snippet={last_user[:120]}"

    def generate_text(
        self,
        user_prompt: str,
        *,
        system_prompt: str = "You are a helpful assistant.",
        model: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: Optional[int] = None,
        timeout: float = 20.0,
    ) -> str:
        return self.generate(
            [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
            model=model, temperature=temperature, max_tokens=max_tokens, timeout=timeout
        )

# --- OpenAI 예시(설치/키 없으면 자동 폴백) ---
@dataclass
class OpenAIClient(LLMClient):
    api_key: str
    default_model: str = "gpt-4o-mini"

    def __post_init__(self):
        try:
            # openai>=1.x
            from openai import OpenAI  # type: ignore
            self._OpenAI = OpenAI
            self._ok = bool(self.api_key)
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
            return NoopClient().generate(messages, model=model, temperature=temperature, max_tokens=max_tokens, timeout=timeout)

        m = model or self.default_model
        delay = 1.0
        for _ in range(3):
            try:
                client = self._OpenAI(api_key=self.api_key)  # type: ignore
                resp = client.chat.completions.create(
                    model=m,
                    messages=messages,            # [{"role": "...", "content":"..."}]
                    temperature=temperature,
                    max_tokens=max_tokens,
                    timeout=timeout,
                )
                return resp.choices[0].message.content or ""
            except Exception:
                time.sleep(delay)
                delay *= 2
        return "[OpenAIClient ERROR] failed after retries."

    def generate_text(
        self,
        user_prompt: str,
        *,
        system_prompt: str = "You are a helpful assistant.",
        model: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: Optional[int] = None,
        timeout: float = 20.0,
    ) -> str:
        return self.generate(
            [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
            model=model, temperature=temperature, max_tokens=max_tokens, timeout=timeout
        )

# --- 팩토리 ---
def get_llm_client() -> LLMClient:
    provider = os.getenv("LLM_PROVIDER", "noop").lower()
    if provider in ("openai", "oai"):
        key = os.getenv("LLM_API_KEY", "")
        return OpenAIClient(api_key=key)
    return NoopClient()