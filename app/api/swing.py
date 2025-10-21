"""
왜 파라미터를 열었나?
- Swagger에서 바로 튜닝/비교 가능(side, min_vis, norm_mode).
- 좌/우타/가시성 임계치에 따라 결과가 크게 달라질 수 있어 빠른 검증이 중요.
"""

from typing import Optional

from fastapi import APIRouter, UploadFile, File, Query
from app.analyze.service import analyze_swing, analyze_from_url
from app.analyze.schema import AnalyzeResponse, UrlRequest, NormMode, ClubType
import os, shutil, uuid

router = APIRouter(prefix="/analyze", tags=["Golf Swings"])

"""
   왜 response_model을 없앴나?
   - B안(요약 응답)에서는 service가 dict로 필요한 키만 반환
   - Pydantic 모델이 끼면 모델에 없는 키가 잘리거나 None으로 들어가 null이 생김
   - dict 그대로 반환하면 service의 결과를 있는 그대로 전달
"""


@router.post("", tags=["Swing"])  # ← response_model 제거
async def analyze(
    file: UploadFile = File(...),
    side: str = Query("right", regex="^(right|left)$"),  # 좌/우타
    min_vis: float = Query(0.5, ge=0.0, le=1.0),  # 가시성 임계치
    norm_mode: NormMode = Query(NormMode.auto),  # 전처리 모드
    club: Optional[ClubType] = Query(None),
):
    os.makedirs("uploads", exist_ok=True)
    file_id = uuid.uuid4().hex[:8]
    file_path = f"uploads/{file_id}_{file.filename}"

    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # service가 요약 응답(딕셔너리)만 돌려줌
    return analyze_swing(
        file_path, side=side, min_vis=min_vis, norm_mode=norm_mode, club=club
    )


@router.post("/url", tags=["Swing"])
async def analyze_url(
    data: UrlRequest,
    side: str = Query("right", regex="^(right|left)$"),
    min_vis: float = Query(0.5, ge=0.0, le=1.0),
):
    return analyze_from_url(
        data.s3_url,
        side=side,
        min_vis=min_vis,
        norm_mode=(data.norm_mode or NormMode.auto),
    )


ROUTER = [router]
