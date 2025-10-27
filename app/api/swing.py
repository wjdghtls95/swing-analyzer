from __future__ import annotations
from typing import Optional

from fastapi import APIRouter, UploadFile, File, Query, Body
from app.analyze.service import analyze_swing
from app.analyze.schema import NormMode, ClubType
from app.utils.enums.enums import SideEnum

import os, shutil, uuid

from app.utils.types.types import LLMConfig

router = APIRouter(prefix="/analyze", tags=["Analyze"])

"""
   왜 response_model을 없앴나?
   - B안(요약 응답)에서는 service가 dict로 필요한 키만 반환
   - Pydantic 모델이 끼면 모델에 없는 키가 잘리거나 None으로 들어가 null이 생김
   - dict 그대로 반환하면 service의 결과를 있는 그대로 전달
"""


@router.post(path="")  # ← response_model 제거
async def analyze(
    file: UploadFile = File(...),
    side: SideEnum = Query(SideEnum.right),  # Swagger 드롭 다운 (좌/우타)
    min_vis: float = Query(0.5, ge=0.0, le=1.0),  # 가시성 임계치
    norm_mode: NormMode = Query(NormMode.auto),  # 전처리 모드
    club: Optional[ClubType] = Query(None),
    llm: LLMConfig = Body(...),  # Body(JSON)로 LLM 설정 일괄 수신
):
    os.makedirs("uploads", exist_ok=True)
    file_id = uuid.uuid4().hex[:8]
    file_path = f"uploads/{file_id}_{file.filename}"

    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # service가 요약 응답(딕셔너리)만 돌려줌
    return analyze_swing(
        file_path,
        side=side.value,
        min_vis=min_vis,
        norm_mode=norm_mode,
        club=club,
        llm_provider=llm.provider,
        llm_model=llm.model,
        llm_api_key=llm.api_key,
        llm_extra={"vendor": llm.vendor, **llm.extra},
    )


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
