from __future__ import annotations

import json, os, shutil, uuid
from typing import Optional

from fastapi import APIRouter, UploadFile, File, Body, HTTPException, status
from pydantic import BaseModel, Field

from app.analyze.service import analyze_swing
from app.analyze.schema import NormMode, ClubType
from app.utils.types.types import LLMConfig
from app.utils.enums.enums import SideEnum
from app.config.settings import settings



router = APIRouter(prefix="/analyze", tags=["Analyze"])

"""
   왜 response_model을 없앴나?
   - B안(요약 응답)에서는 service가 dict로 필요한 키만 반환
   - Pydantic 모델이 끼면 모델에 없는 키가 잘리거나 None으로 들어가 null이 생김
   - dict 그대로 반환하면 service의 결과를 있는 그대로 전달
"""
class AnalyzeRequest(BaseModel):
    """
    /run 엔드포인트를 위한 Request Body 모델입니다.
    File 대신 file_path를 받고, LLM 설정을 JSON 객체로 직접 받습니다.
    """
    file_path: str = Field(..., description="[Step 1]에서 반환받은 파일 경로")
    side: SideEnum = Field(SideEnum.right, description="스윙 방향")
    min_vis: float = Field(0.5, ge=0.0, le=1.0, description="최소 가시성")
    norm_mode: NormMode = Field(NormMode.auto, description="전처리 모드")
    club: Optional[ClubType] = Field(None, description="클럽 종류")
    llm: Optional[LLMConfig] = Field(None, description="LLM 설정 (JSON 객체)")

    # 모델 예시 데이터 (Swagger UI에 표시됨)
    class Config:
        json_schema_extra = {
            "example": {
                "file_path": "uploads/abcdef12_swing.mp4",
                "side": "right",
                "min_vis": 0.5,
                "norm_mode": "auto",
                "club": "driver",
                "llm": {
                    "provider": "openai",
                    "vendor": "openai",
                    "model": "gpt-4o-mini",
                    "api_key": "sk-proj-..."
                }
            }
        }

@router.post(
    "/upload",
    summary="[Step 1] 스윙 영상 업로드",
    description="스윙 영상을 서버에 업로드 & 저장된 파일 경로를 반환"
)
async def upload_video(
        file: UploadFile = File(..., description="분석할 스윙 영상")
):
    # 1) 파일 저장 디렉토리 확인
    os.makedirs("uploads", exist_ok=True)

    # 2) 고유 파일명 생성
    file_id = uuid.uuid4().hex[:8]
    file_path = f"uploads/{file_id}_{file.filename}"

    # 3) 파일 저장
    try:
        with open(file_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
    except Exception as e:
        # 파일 저장 중 오류 발생 시
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"File could not be saved: {e}"
        )
    finally:
        file.file.close()  # 파일 핸들러 닫기

    # 4) 저장된 경로 반환
    return {"file_path": file_path}



@router.post(
    "/run",
    summary="[Step 2] 분석 실행 (JSON)",
    description="업로드된 파일 경로와 JSON 설정을 받아 스윙 분석을 실행합니다."
)
async def analyze(
        request: AnalyzeRequest = Body(...)  # <--- Body를 통해 깔끔한 JSON으로 받음
):
    # 1) 파일 존재 여부 확인 (Robustness)
    if not os.path.exists(request.file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File not found at path: {request.file_path}. Please upload the file first via /analyze/upload"
        )

    # 2) LLM 파라미터 구성 (매우 깔끔해짐)
    llm = request.llm
    if llm:
        provider = llm.provider or settings.LLM_DEFAULT_PROVIDER or "noop"
        model = llm.model or settings.LLM_DEFAULT_MODEL
        api_key = llm.api_key or settings.OPENAI_API_KEY
        extra = {"vendor": (llm.vendor or "openai"), **(llm.extra or {})}
    else:
        provider, model, api_key, extra = "noop", "noop", None, {"vendor": "noop"}

    # 3) 분석 서비스 호출 (request 객체에서 값 사용)
    return analyze_swing(
        file_path=request.file_path,
        side=request.side.value,
        min_vis=request.min_vis,
        norm_mode=request.norm_mode,
        club=request.club,
        llm_provider=provider,
        llm_model=model,
        llm_api_key=api_key,
        llm_extra=extra,
    )



# @router.post("")
# async def analyze(
#     file: UploadFile = File(..., description="분석할 스윙 영상"),
#     side: SideEnum = Query(SideEnum.right, description="스윙 방향"),
#     min_vis: float = Query(0.5, ge=0.0, le=1.0),
#     norm_mode: NormMode = Query(NormMode.auto, description="전처리 모드"),
#     club: Optional[ClubType] = Query(None, description="클럽 종류"),
#     llm_json: Optional[str] = Form(
#         None,
#         description=(
#             "LLM 설정 JSON. 생략하면 NOOP 폴백.\n"
#             '예시: {"provider":"openai","vendor":"openai","model":"gpt-4o-mini","api_key":"sk-proj-..."}'
#         ),
#     ),   # ← 선택 입력(없으면 NOOP 폴백)
# ):
#     # 1) LLM 설정 파싱(없으면 NOOP)
#     llm: Optional[LLMConfig] = None
#     if llm_json:
#         try:
#             llm = LLMConfig.model_validate_json(llm_json)
#         except ValidationError as e:
#             # 형식이 이상하면 바로 NOOP로
#             llm = None
#         except Exception:
#             try:
#                 llm = LLMConfig.model_validate(json.loads(llm_json))
#             except Exception:
#                 llm = None
#
#     # 2) 파일 저장
#     os.makedirs("uploads", exist_ok=True)
#     file_id = uuid.uuid4().hex[:8]
#     file_path = f"uploads/{file_id}_{file.filename}"
#     with open(file_path, "wb") as f:
#         shutil.copyfileobj(file.file, f)
#
#     # 3) LLM 파라미터 구성 (없으면 NOOP)
#     if llm:
#         provider = llm.provider or settings.LLM_DEFAULT_PROVIDER or "noop"
#         model = llm.model or settings.LLM_DEFAULT_MODEL
#         api_key = llm.api_key or settings.OPENAI_API_KEY
#         extra = {"vendor": (llm.vendor or "openai"), **(llm.extra or {})}
#     else:
#         provider, model, api_key, extra = "noop", "noop", None, {"vendor": "noop"}
#
#     # 4) 호출
#     return analyze_swing(
#         file_path=file_path,
#         side=side.value,
#         min_vis=min_vis,
#         norm_mode=norm_mode,
#         club=club,
#         llm_provider=provider,
#         llm_model=model,
#         llm_api_key=api_key,
#         llm_extra=extra,
#     )

# ================================
# s3 도입시 사용할 api
# ================================
# @router.post(path="url")
# async def analyze_url(
#     data: UrlRequest,
#     side: str = Query("right", pattern="^(right|left)$"),
#     min_vis: float = Query(0.5, ge=0.0, le=1.0),
#
#     llm_provider: LLMProviderEnum = Query(settings.LLM_DEFAULT_PROVIDER),
#     llm_model: Optional[str] = Query(None),
#     llm_api_key: Optional[str] = Query(None),
# ):
#     return analyze_from_url(
#         data.s3_url,
#         side=side,
#         min_vis=min_vis,
#         norm_mode=(data.norm_mode or NormMode.auto),
#         llm_provider=llm_provider.value,
#         llm_model=llm_model,
#         llm_api_key=llm_api_key,
#     )

ROUTER = [router]
