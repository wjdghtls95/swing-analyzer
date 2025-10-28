from __future__ import annotations
from typing import List, Optional, Dict, Callable, Any
import time
import requests
import logging

from app.config.settings import settings
from app.utils.types.types import Message
from app.llm.providers.openai_runtime import get_openai_adapter

logger = logging.getLogger(__name__)

Provider = str

"""
단일 클래스 내부에 provider별 핸들러 등록.
- gateway: 경량 게이트웨이 (헤더 인증)
- noop   : 개발/테스트
"""


class DelegateLLMClient:
    """
    - Provider 딕셔너리로 확장 용이
    - 모든 상수/기본값은 settings에서만 가져옴
    """
    def __init__(self):
        self.default_provider: Provider = settings.LLM_DEFAULT_PROVIDER # ex) openai, gemini...
        self.default_model: str = settings.LLM_DEFAULT_MODEL

        # Provider 핸들러 맵(필요 시 register로 확장 가능) => Delegate Pattern
        self._handlers: Dict[str, Callable[..., str]] = {
            "gateway": self._gateway_generate,
            "noop": self._noop_generate,
        }

    def generate(
        self,
        messages: List[Message],
        *,
        provider: Optional[Provider] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        timeout: float = 20.0,
        api_key_override: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> str:
        chosen = provider or self.default_provider
        handler = self._handlers.get(chosen, self._noop_generate)

        return handler(
            messages,
            model=(model or self.default_model),
            temperature=(
                temperature
                if temperature is not None
                else settings.LLM_TEMPERATURE_DEFAULT
            ),
            max_tokens=(
                max_tokens
                if max_tokens is not None
                else settings.LLM_MAX_TOKENS_DEFAULT
            ),
            timeout=timeout,
            api_key_override=api_key_override,
            extra=(extra or {}),
        )

    # Handlers
    def _gateway_generate(
            self,
            messages: List[Message],
            *,
            model: str,
            temperature: float,
            max_tokens: Optional[int],
            timeout: float,
            api_key_override: Optional[str],
            extra: Dict[str, Any],
    ) -> str:
        """
        경량 게이트웨이 호출: 헤더 Authorization(Bearer <KEY>) 필요.
        extra:
          - vendor: 실제 엔진 식별자(openai/gemini/groq/..)
        """
        endpoint = extra.get("mcp_endpoint") or settings.LLM_GATEWAY_ENDPOINT
        headers = {
            "Authorization": f"Bearer {settings.LLM_GATEWAY_KEY}",
            "Content-Type": "application/json",
        }
        payload: Dict[str, Any] = {
            "provider": extra.get("vendor", "openai"),
            "transport": extra.get("transport"),
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "extra": {
                k: v
                for k, v in extra.items()
                if k not in {"vendor", "transport", "mcp_endpoint"}
            },
        }
        delay = 0.6

        for _ in range(3):
            try:
                r = requests.post(
                    endpoint, json=payload, headers=headers, timeout=timeout
                )
                if r.status_code == 200:
                    return (r.json().get("content") or "").strip()
                if r.status_code in (429, 500, 502, 503, 504):
                    time.sleep(delay)
                    delay *= 2
                    continue
                return f"[GATEWAY ERROR] {r.status_code} {r.text[:200]}"
            except Exception:
                time.sleep(delay)
                delay *= 2
        return "[GATEWAY ERROR] upstream failed."

    # Test - 파이프라인 및 로직 확인 시 사용
    def _noop_generate(
                self,
                messages: List[Message],
                *,
                model: str,
                temperature: float,
                max_tokens: Optional[int],
                timeout: float,
                api_key_override: Optional[str],
                extra: Dict[str, Any],
    ) -> str:
        last_user = next(
            (m["content"] for m in reversed(messages) if m["role"] == "user"), ""
        )

        return f"[NOOP] model={model} messages={len(messages)} last_user={last_user[:120]}"