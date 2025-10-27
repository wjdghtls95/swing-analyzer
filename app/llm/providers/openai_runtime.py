"""
OpenAI SDK를 필요할 때만 동적으로 import하고, 그 성공/실패 결과를 전역 캐시에 저장해 다음 호출부터는 즉시 재사용하는 지연 로딩(lazy import) + 캐시 헬퍼
"""

from __future__ import annotations
import importlib, threading, logging
from typing import Any, Optional, List, Dict
from app.utils.types.types import Message

logger = logging.getLogger(__name__)
_lock = threading.Lock()

_cache: Dict[str, Any] = {
    "OpenAI": None,  # openai.OpenAI 클래스
    "available": None,  # import 가능 여부
}


def _import_openai_cls() -> Optional[type]:
    if _cache["available"] is True:
        return _cache["OpenAI"]
    if _cache["available"] is False:
        return None
    with _lock:
        if _cache["available"] is not None:
            return _cache["OpenAI"]
        try:
            mod = importlib.import_module("openai")
            OpenAI = getattr(mod, "OpenAI")
            _cache["OpenAI"] = OpenAI
            _cache["available"] = True
            logger.info("[LLM] OpenAI SDK loaded (lazy)")
            return OpenAI
        except Exception as e:
            _cache["available"] = False
            logger.warning(f"[LLM] OpenAI SDK import failed: {e}")
            return None


class _OpenAIChatAdapter:
    """SDK 차단/의존성 분리를 위한 어댑터: .chat() 만 노출"""

    def __init__(self, api_key: str):
        OpenAI = _import_openai_cls()
        if not OpenAI:
            raise RuntimeError("OpenAI SDK unavailable")
        self._client = OpenAI(api_key=api_key)

    def chat(
        self,
        *,
        model: str,
        messages: List[Message],
        temperature: float,
        max_tokens: Optional[int],
        timeout: float,
    ) -> str:
        resp = self._client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
        )
        return (resp.choices[0].message.content or "").strip()


def get_openai_adapter(api_key: str) -> _OpenAIChatAdapter:
    """성공 시 SDK 래퍼, 실패 시 예외(상위에서 STUB/Fallback)"""
    return _OpenAIChatAdapter(api_key=api_key)
