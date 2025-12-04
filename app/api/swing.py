from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
import os
import logging

from app.schemas.analyze_dto import AnalyzeSwingRequest, AnalyzeSwingResponse
from app.schemas.analyze_request import AnalyzeSwingApiRequest
from app.services.service_factory import create_swing_analysis_service
from app.config.settings import settings
from app.common.dependencies import verify_api_key, parse_analyze_request

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/analyze", tags=["Swing Analysis"])

# ========== API Endpoint ==========
@router.post("", response_model=AnalyzeSwingResponse)
async def analyze_swing(
        file: UploadFile = File(..., description="스윙 비디오 파일"),
        req: AnalyzeSwingApiRequest = Depends(parse_analyze_request),
        _: bool = Depends(verify_api_key)
) -> AnalyzeSwingResponse:
    """
    골프 스윙 분석 API

    기본: llm_provider="noop" (테스트, 무과금)
    실제: llm_provider="openai" (과금)
    """
    logger.info(f"📥 분석 요청: user={req.user_id}, club={req.club}, llm={req.llm_provider}")

    # 1. 파일 저장
    upload_dir = settings.UPLOADS_DIR
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, file.filename)

    try:
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        logger.info(f"✅ 파일 저장: {file_path}")
    except Exception as e:
        logger.error(f"❌ 파일 저장 실패: {e}")
        raise HTTPException(status_code=500, detail=f"파일 저장 실패: {e}")

    # 2. Factory로 Service 생성
    service = create_swing_analysis_service(
        club=req.club,
        swing_direction=req.swing_direction,
        visibility_threshold=req.visibility_threshold,
        llm_provider=req.llm_provider,
        llm_model=req.llm_model
    )

    # 3. Service DTO 생성
    request = AnalyzeSwingRequest(
        file_path=file_path,
        user_id=req.user_id,
        club=req.club,
        swing_direction=req.swing_direction,
        visibility_threshold=req.visibility_threshold,
        normalize_mode=req.normalize_mode,
        llm_provider=req.llm_provider,
        llm_model=req.llm_model
    )

    # 4. 분석 실행
    try:
        logger.info("🔄 스윙 분석 시작...")
        result = await service.analyze(request)
        logger.info(f"✅ 스윙 분석 완료: {result.analysis_id}")
        return result

    except Exception as e:
        logger.error(f"❌ 분석 실패: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"분석 실패: {e}")

    finally:
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"🗑️ 임시 파일 삭제: {file_path}")

# @router.post("", response_model=AnalyzeSwingResponse)
# async def analyze(
#     file: UploadFile = File(..., description="분석할 스윙 영상 (mp4 등)"),
#     req: AnalyzeSwingApiRequest = Depends(AnalyzeSwingApiRequest.as_form),
#     _: bool = Depends(verify_api_key),
# ) -> AnalyzeSwingResponse:
#     upload_dir = settings.UPLOADS_DIR
#     os.makedirs(upload_dir, exist_ok=True)
#
#     file_path = os.path.join(upload_dir, file.filename)
#     try:
#         # 파일 저장
#         with open(file_path, "wb") as f:
#             content = await file.read()
#             f.write(content)
#
#
#
#         # Service용 Request DTO
#         request = AnalyzeSwingRequest(
#             file_path=file_path,
#             user_id=req.user_id or "anonymous",
#             club=req.club,
#             swing_direction=req.swing_direction,
#             visibility_threshold=req.visibility_threshold,
#             normalize_mode=req.normalize_mode,
#             llm_provider=req.llm_provider,
#             llm_model=req.llm_model,
#         )
#
#         service = get_swing_analysis_service()
#
#         result = await service.analyze(service_request)
#
#         return result
#
#     except Exception as e:
#         logger.exception("❌ 스윙 분석 중 오류 발생")
#         raise HTTPException(status_code=500, detail=f"분석 실패: {str(e)}")
#
#     finally:
#         if os.path.exists(file_path):
#             os.remove(file_path)

ROUTER = [router]