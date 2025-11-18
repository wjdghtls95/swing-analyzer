from __future__ import annotations
from typing import Optional, Dict, Any

import httpx
import logging

from app.config.settings import settings

logger = logging.getLogger(__name__)

Provider = str

class LLMGatewayClient:
    """
    - Provider 딕셔너리로 확장 용이
    - 모든 상수/기본값은 settings에서만 가져옴
    """

    def __init__(self):
        self.gateway_url = settings.LLM_GATEWAY_URL
        self.api_key = settings.INTERNAL_API_KEY

        # URL이 /chat으로 끝나지 않으면 붙여주는 안전장치
        if not self.gateway_url.endswith("/chat"):
            self.gateway_url = f"{self.gateway_url.rstrip('/')}/chat"

    def chat_summary_gateway(
            self,
            analysis_data: Dict[str, Any],
            model: Optional[str] = None,
            provider: Optional[str] = None,
            language: str = "ko"
    ) -> str:
        """LLM Gateway를 호출합니다 (POST /chat)"""
        if not self.gateway_url:
            raise ValueError("LLM_GATEWAY_URL is not set")

        payload = {
            "provider": provider or settings.LLM_DEFAULT_PROVIDER,
            "model": model or settings.LLM_DEFAULT_MODEL,
            "language": language,
            "analysisData": analysis_data
        }

        headers = {
            "Content-Type": "application/json",
            "X-Internal-API-Key": self.api_key,  # (플로우 7번) 내부 인증: 서비스 key_B
        }

        try:
            # httpx 사용 (requests보다 최신 라이브러리, 동기 호출)
            with httpx.Client(timeout=60.0) as client:
                response = client.post(
                    self.gateway_url,
                    json=payload,
                    headers=headers
                )

                if response.status_code != 200:
                    logger.error(f"LLM Gateway Error: {response.status_code} - {response.text}")
                    return f"분석 실패 (Gateway Error: {response.status_code})"

                # NestJS가 { "feedback": "..." } 형태로 준다고 가정
                data = response.json()
                return data.get("feedback", "")

        except Exception as e:
            logger.error(f"LLM Gateway Connection Failed: {e}")
            return f"분석 실패 (연결 오류: {str(e)})"