from fastapi import Header, HTTPException, Form
from typing import Optional, Literal
from app.config.settings import settings
from app.schemas.analyze_request import AnalyzeSwingApiRequest
import logging

logger = logging.getLogger(__name__)


# API Key 인증
async def verify_api_key(
        x_internal_api_key: Optional[str] = Header(None, alias="X-Internal-Api-Key")
):
    if x_internal_api_key is None:
        logger.warning("⚠️ Missing X-Internal-Api-Key header")
        raise HTTPException(
            status_code=401,
            detail="Missing X-Internal-Api-Key header"
        )

    if x_internal_api_key != settings.INTERNAL_API_KEY:
        logger.warning(f"❌ Invalid API Key: {x_internal_api_key[:10]}...")
        raise HTTPException(
            status_code=401,
            detail="Invalid Internal API Key"
        )

    logger.info("✅ API Key 인증 성공")
    return True  # 기존 코드 호환


# Form 데이터 → DTO 변환
async def parse_analyze_request(
        user_id: Optional[str] = Form(
            default=None,
            description="사용자 ID (개인화 기능용, 없으면 익명)"
        ),
        club: Literal["driver", "iron", "wedge"] = Form(
            ...,
            description="클럽 종류"
        ),
        swing_direction: Literal["right", "left"] = Form(
            default="right",
            description="스윙 방향 (우타/좌타)"
        ),
        visibility_threshold: float = Form(
            default=0.5,
            ge=0.0,
            le=1.0,
            description="MediaPipe 포즈 가시성 임계값"
        ),
        normalize_mode: Literal["height", "shoulder"] = Form(
            default="height",
            description="각도 정규화 모드 (height: 키 기준, shoulder: 어깨 기준)"
        ),
        llm_provider: Optional[Literal['noop', "openai", "anthropic"]] = Form(
            default='noop',
            description="LLM 제공자 (noop: 테스트, openai: OpenAI API, anthropic: Claude API)"
        ),
        llm_model: Optional[str] = Form(
            default=None,
            description="LLM 모델명 (예: gpt-4o-mini)"
        ),
) -> AnalyzeSwingApiRequest:
    """
    FastAPI Form 데이터를 AnalyzeSwingApiRequest DTO로 변환

    왜 필요한가?
    - FastAPI는 기본적으로 Form 데이터를 개별 파라미터로 받음
    - 8개의 개별 파라미터 → 1개의 구조화된 DTO 객체로 변환
    - Pydantic validation 적용 (타입 체크, 범위 검증)

    사용법:
        @app.post("/analyze/")
        async def analyze_swing(
            api_request: AnalyzeSwingApiRequest = Depends(parse_analyze_request)
        ):
            # api_request.user_id, api_request.club 등 사용
    """
    return AnalyzeSwingApiRequest(
        user_id=user_id,
        club=club,
        swing_direction=swing_direction,
        visibility_threshold=visibility_threshold,
        normalize_mode=normalize_mode,
        llm_provider=llm_provider,
        llm_model=llm_model
    )