import httpx
from typing import Optional
import logging
from app.schemas.diagnosis_dto import DiagnosisResult
from app.config.settings import settings

logger = logging.getLogger(__name__)

class LLMGatewayClient:
    """LLM Gateway와 통신하는 클라이언트"""

    def __init__(
        self,
        gateway_url: str,
        provider: str = "noop",
        model: str = "gpt-4o-mini",
        api_key: Optional[str] = None,
        timeout: int = 30
    ):
        """
        Args:
            gateway_url: LLM Gateway 서버 URL (예: http://localhost:3030)
            provider: LLM 제공자 (noop, openai, anthropic 등)
            model: 모델명
            api_key: API 키 (optional, Gateway에서 관리할 수도 있음)
            timeout: 타임아웃(초)
        """
        self.gateway_url = gateway_url.rstrip("/")
        self.provider=provider.lower()
        self.model = model
        self.api_key = api_key
        self.timeout = timeout

        if self.provider == 'noop':
            logger.info("🧪 LLM Client: NoOp 모드 (테스트용, 과금 없음)")
        else:
            logger.info(f"🚀 LLM Client: {provider} / {model}")


    def generate_feedback(
        self,
        diagnosis: DiagnosisResult,
        user_id: str,
        club: str,
        tone: str = "professional",
        language: str = "ko"
    ) -> str:
        """
        진단 결과 기반 AI 피드백 생성

        Args:
            diagnosis: 진단 결과
            user_id: 사용자 ID
            club: 클럽 종류
            tone: 어조 (professional, friendly, coach)
            language: 언어 (ko, en)

        Returns:
            AI가 생성한 피드백 텍스트
        """
        # noop 모드- mock 응답 즉시 return
        if self.provider == "noop":
            logger.info("Noop 모드: Mock 응답 반환 (과금 없음)")
            return self._generate_mock_feedback(diagnosis)

        # System prompt
        system_prompt = self._build_system_prompt(tone, language)

        # User prompt (진단 요약)
        user_prompt = self._build_user_prompt(diagnosis, club)

        # LLM Gateway 호출
        try:
            response = httpx.post(
                f"{self.gateway_url}/api/chat",
                json={
                    "provider": self.provider,
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "user_id": user_id,
                    "temperature": 0.7,
                    "max_tokens": 500
                },
                headers={"X-API-Key": self.api_key} if self.api_key else {},
                timeout=self.timeout
            )
            response.raise_for_status()

            result = response.json()
            return result.get("content", "피드백 생성 실패")

        except httpx.HTTPError as e:
            # Fallback: 룰 기반 피드백
            return self._fallback_feedback(diagnosis)

    def _build_system_prompt(self, tone: str, language: str) -> str:
        """System prompt 생성"""
        tone_map = {
            "professional": "전문적이고 객관적인",
            "friendly": "친근하고 격려하는",
            "coach": "코치처럼 구체적인 실천 방안을 제시하는"
        }

        tone_desc = tone_map.get(tone, "전문적이고 객관적인")

        if language == "ko":
            return f"""당신은 프로 골프 코치입니다.
스윙 분석 결과를 바탕으로 {tone_desc} 어조로 피드백을 제공하세요.

요구사항:
- 5-8문장으로 간결하게 작성
- 가장 중요한 문제점 2-3개만 언급
- 구체적인 개선 방법 제시
- 긍정적인 부분도 함께 언급
"""
        else:  # English
            return f"""You are a professional golf coach.
Provide feedback based on swing analysis results in a {tone_desc} tone.

Requirements:
- Keep it concise (5-8 sentences)
- Mention only 2-3 most important issues
- Provide specific improvement methods
- Include positive aspects as well
"""

    def _build_user_prompt(self, diagnosis: DiagnosisResult, club: str) -> str:
        """User prompt (진단 요약) 생성"""
        lines = [f"클럽: {club}", f"전체 점수: {diagnosis.overall_score:.1f}/100", ""]

        for d in diagnosis.diagnoses:
            lines.append(f"[{d.phase}] 점수: {d.score:.1f}")
            if d.issues:
                lines.append(f"  문제점: {', '.join(d.issues[:2])}")  # 최대 2개만

        return "\n".join(lines)

    def _fallback_feedback(self, diagnosis: DiagnosisResult) -> str:
        """LLM 실패 시 룰 기반 피드백"""
        feedback_lines = [f"스윙 전체 점수: {diagnosis.overall_score:.1f}/100"]

        # 가장 낮은 점수 페이즈 찾기
        worst_phase = min(diagnosis.diagnoses, key=lambda d: d.score)

        feedback_lines.append(f"\n가장 개선이 필요한 단계: {worst_phase.phase} (점수: {worst_phase.score:.1f})")

        if worst_phase.issues:
            feedback_lines.append("\n주요 문제점:")
            for issue in worst_phase.issues[:2]:
                feedback_lines.append(f"- {issue}")

        if worst_phase.suggestions:
            feedback_lines.append("\n개선 제안:")
            for suggestion in worst_phase.suggestions[:2]:
                feedback_lines.append(f"- {suggestion}")

        return "\n".join(feedback_lines)

    def _generate_mock_feedback(self, diagnosis: DiagnosisResult) -> str:
        """
        Noop 모드용 Mock 피드백 생성

        Args:
            diagnosis: 진단 결과

        Returns:
            Mock 피드백 텍스트
        """
        feedback_lines = [
            "[테스트 모드 - NoOp LLM]",
            "",
            f"✅ 스윙 분석이 정상적으로 완료되었습니다.",
            f"전체 점수: {diagnosis.overall_score:.1f}/100",
            ""
        ]

        # 가장 낮은 점수 페이즈 찾기
        if diagnosis.diagnoses:
            worst_phase = min(diagnosis.diagnoses, key=lambda d: d.score)
            feedback_lines.append(f"개선이 필요한 단계: {worst_phase.phase} (점수: {worst_phase.score:.1f})")

            if worst_phase.issues:
                feedback_lines.append("")
                feedback_lines.append("주요 문제점:")
                for issue in worst_phase.issues[:2]:
                    feedback_lines.append(f"- {issue}")

        feedback_lines.extend([
            "",
            "현재는 테스트 모드로, 실제 LLM API를 호출하지 않습니다.",
            "과금이 발생하지 않습니다.",
            "",
            "실제 AI 피드백을 받으려면:",
            "1. Swagger UI에서 llm_provider를 'openai'로 변경",
            "2. llm_model을 'gpt-4o-mini' 등으로 설정",
            "3. Execute 실행"
        ])
        
        return "\n".join(feedback_lines)

    def generate_text(
        self,
        user_prompt: str,
        system_prompt: str = "",
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 500,
        timeout: float = 30.0
    ) -> str:
        """
        일반적인 텍스트 생성 (보고서 등)
        
        Args:
            user_prompt: 사용자 프롬프트
            system_prompt: 시스템 프롬프트
            model: 모델명 (없으면 self.model 사용)
            temperature: 온도
            max_tokens: 최대 토큰
            timeout: 타임아웃
            
        Returns:
            생성된 텍스트
        """
        # noop 모드: mock 응답
        if self.provider == "noop":
            logger.info("Noop 모드: Mock 텍스트 반환")
            return self._generate_mock_text(user_prompt)
        
        # LLM Gateway 호출
        try:
            response = httpx.post(
                f"{self.gateway_url}/api/chat",
                json={
                    "provider": self.provider,
                    "model": model or self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "temperature": temperature,
                    "max_tokens": max_tokens
                },
                headers={"X-API-Key": self.api_key} if self.api_key else {},
                timeout=timeout
            )
            response.raise_for_status()
            result = response.json()
            return result.get("content", "텍스트 생성 실패")
        
        except httpx.HTTPError as e:
            logger.error(f"LLM Gateway 호출 실패: {e}")
            return self._generate_fallback_text(user_prompt)
    
    def _generate_mock_text(self, user_prompt: str) -> str:
        """Noop 모드용 Mock 텍스트"""
        return f"""[테스트 모드 - NoOp LLM]

이것은 실제 LLM API를 호출하지 않고 반환되는 Mock 응답입니다.
과금이 발생하지 않습니다.

입력된 프롬프트:
{user_prompt[:200]}...

실제 AI 응답을 받으려면 llm_provider를 'openai' 또는 'anthropic'으로 설정하세요.
"""
    
    def _generate_fallback_text(self, user_prompt: str) -> str:
        """LLM 실패 시 Fallback 텍스트"""
        return f"""[LLM 서비스 일시적 오류]

죄송합니다. AI 서비스 연결에 문제가 발생했습니다.
잠시 후 다시 시도해주세요.

입력된 프롬프트: {user_prompt[:100]}...
"""


def get_llm_client(
    provider: Optional[str] = None,
    model: Optional[str] = None,
    gateway_url: Optional[str] = None,
    api_key: Optional[str] = None
) -> LLMGatewayClient:
    """
    LLM 클라이언트 팩토리 함수
    
    Args:
        provider: LLM 제공자 (없으면 settings에서 가져옴)
        model: 모델명 (없으면 settings에서 가져옴)
        gateway_url: Gateway URL (없으면 settings에서 가져옴)
        api_key: API 키 (없으면 settings에서 가져옴)
        
    Returns:
        LLMGatewayClient 인스턴스
    """
    return LLMGatewayClient(
        gateway_url=gateway_url or settings.LLM_GATEWAY_URL,
        provider=provider or settings.LLM_DEFAULT_PROVIDER,
        model=model or settings.LLM_DEFAULT_MODEL,
        api_key=api_key or settings.OPENAI_API_KEY,
        timeout=30
    )