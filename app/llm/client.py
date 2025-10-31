from __future__ import annotations
from typing import List, Optional, Dict, Callable, Any
import time
import requests
import logging

from app.config.settings import settings
from app.utils.types.types import Message

logger = logging.getLogger(__name__)

Provider = str
class LLMGatewayClient:
    """
    - Provider 딕셔너리로 확장 용이
    - 모든 상수/기본값은 settings에서만 가져옴
    """

    def __init__(self, internal_api_key: Optional[str] = None):
        self.internal_api_key = (
                internal_api_key or settings.INTERNAL_API_KEY
        )
        self.gateway_url = settings.LLM_GATEWAY_URL

    def chat_summary_gateway(self, analysis_data: Dict[str, Any], **kwargs) -> str:
        """LLM Gateway를 호출합니다 (POST /chat)"""
        if not self.gateway_url:
            raise ValueError("LLM_GATEWAY_URL is not set")

        headers = {
            "Content-Type": "application/json",
            "X-Internal-API-Key": self.internal_api_key,  # (플로우 7번) 내부 인증
        }

        # 이유: kwargs에 language='ko' 등이 포함됩니다.
        payload = {"analysisData": analysis_data, "options": kwargs}

        response = requests.post(
            f"{self.gateway_url}/chat", json=payload, headers=headers
        )
        response.raise_for_status()  # 2xx가 아니면 예외 발생

        # 이유: (플로우 11번) 게이트웨이로부터 받은 피드백(text)을 반환합니다.
        return response.json().get("feedback")


    # def generate(
    #         self,
    #         messages: List[Message],
    #         *,
    #         provider: Optional[Provider] = None,
    #         model: Optional[str] = None,
    #         temperature: Optional[float] = None,
    #         max_tokens: Optional[int] = None,
    #         timeout: float = 20.0,
    #         api_key_override: Optional[str] = None,
    #         extra: Optional[Dict[str, Any]] = None,
    # ) -> str:
    #     chosen = provider or self.default_provider
    #     handler = self._handlers.get(chosen, self._noop_generate)
    #
    #     return handler(
    #         messages,
    #         model=(model or self.default_model),
    #         temperature=(
    #             temperature
    #             if temperature is not None
    #             else settings.LLM_TEMPERATURE_DEFAULT
    #         ),
    #         max_tokens=(
    #             max_tokens
    #             if max_tokens is not None
    #             else settings.LLM_MAX_TOKENS_DEFAULT
    #         ),
    #         timeout=timeout,
    #         api_key_override=api_key_override,
    #         extra=(extra or {}),
    #     )


    # Handlers
    # def _gateway_generate(
    #         self,
    #         messages: List[Message],
    #         *,
    #         model: str,
    #         temperature: float,
    #         max_tokens: Optional[int],
    #         timeout: float,
    #         api_key_override: Optional[str],
    #         extra: Dict[str, Any],
    # ) -> str:
    #     """
    #     경량 게이트웨이 호출: 헤더 Authorization(Bearer <KEY>) 필요.
    #     extra:
    #       - vendor: 실제 엔진 식별자(openai/gemini/groq/..)
    #     """
    #     endpoint = extra.get("mcp_endpoint") or settings.LLM_GATEWAY_ENDPOINT
    #     headers = {
    #         "Authorization": f"Bearer {settings.LLM_GATEWAY_KEY}",
    #         "Content-Type": "application/json",
    #     }
    #     payload: Dict[str, Any] = {
    #         "provider": extra.get("vendor", "openai"),
    #         "transport": extra.get("transport"),
    #         "model": model,
    #         "messages": messages,
    #         "temperature": temperature,
    #         "max_tokens": max_tokens,
    #         "extra": {
    #             k: v
    #             for k, v in extra.items()
    #             if k not in {"vendor", "transport", "mcp_endpoint"}
    #         },
    #     }
    #     delay = 0.6
    #
    #     for _ in range(3):
    #         try:
    #             r = requests.post(
    #                 endpoint, json=payload, headers=headers, timeout=timeout
    #             )
    #             if r.status_code == 200:
    #                 return (r.json().get("content") or "").strip()
    #             if r.status_code in (429, 500, 502, 503, 504):
    #                 time.sleep(delay)
    #                 delay *= 2
    #                 continue
    #             return f"[GATEWAY ERROR] {r.status_code} {r.text[:200]}"
    #         except Exception:
    #             time.sleep(delay)
    #             delay *= 2
    #     return "[GATEWAY ERROR] upstream failed."
    #
    # # Test - 파이프라인 및 로직 확인 시 사용
    # def _noop_generate(
    #         self,
    #         messages: List[Message],
    #         *,
    #         model: str,
    #         temperature: float,
    #         max_tokens: Optional[int],
    #         timeout: float,
    #         api_key_override: Optional[str],
    #         extra: Dict[str, Any],
    # ) -> str:
    #     last_user = next(
    #         (m["content"] for m in reversed(messages) if m["role"] == "user"), ""
    #     )
    #
    #     return f"[NOOP] model={model} messages={len(messages)} last_user={last_user[:120]}"

