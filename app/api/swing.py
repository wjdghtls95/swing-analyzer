from __future__ import annotations

import os, shutil, uuid
from typing import Optional

from fastapi import APIRouter, UploadFile, File, Body, HTTPException, status, Form, Header, Depends
from pydantic import BaseModel, Field

from app.analyze.service import analyze_swing
from app.analyze.schema import NormMode, ClubType
from app.utils.enums.enums import SideEnum
from app.config.settings import settings

router = APIRouter(prefix="/analyze", tags=["Analyze"])

# ---------------------------------------------------------
# 1. 보안: API Key 검증 의존성 함수
# ---------------------------------------------------------
async def verify_api_key(x_internal_api_key: Optional[str] = Header(None, alias="X-Internal-Api-Key")):
    """
    헤더에 있는 X-Internal-Api-Key가 환경변수와 일치하는지 확인
    """
    if x_internal_api_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-Internal-Api-Key header"
        )

    if x_internal_api_key != settings.INTERNAL_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Internal API Key"
        )

    return True

class AnalyzeRequest(BaseModel):
    """
    /run 엔드포인트 (테스트용)를 위한 Request Body 모델입니다.
    File 대신 file_path를 받고, LLM 설정을 JSON 객체로 직접 받습니다.
    """
    file_path: str = Field(..., description="[Step 1]에서 반환받은 파일 경로")
    side: SideEnum = Field(SideEnum.right, description="스윙 방향")
    min_vis: float = Field(0.5, ge=0.0, le=1.0, description="최소 가시성")
    norm_mode: NormMode = Field(NormMode.auto, description="전처리 모드")
    club: Optional[ClubType] = Field(None, description="클럽 종류")
    # llm: Optional[LLMConfig] = Field(None, description="LLM 설정 (JSON 객체)")  # dict 으로 받음

    # [수정] 명시적 데이터 필드
    user_id: str = Field(..., description="유저 아이디")
    model_name: Optional[str] = Field(None, description="LLM 모델명 (없으면 기본값)")

    # 모델 예시 데이터 (Swagger UI에 표시됨)
    class Config:
        json_schema_extra = {
            "example": {
                "file_path": "uploads/abcdef12_swing.mp4",
                "side": "right",
                "min_vis": 0.5,
                "norm_mode": "auto",
                "club": "driver",
                "user_id": "123",
                "model_name": "gpt-4o-mini"
            }
        }


@router.post(
    "/upload",
    summary="[Step 1] 스윙 영상 업로드 (테스트 용)",
    description="스윙 영상을 서버에 업로드 & 저장된 파일 경로를 반환"
)
async def upload_video(
        file: UploadFile = File(..., description="분석할 스윙 영상")
):
    # 1) 파일 저장 디렉토리 확인
    os.makedirs(settings.UPLOADS_DIR, exist_ok=True)

    # 2) 고유 파일명 생성
    file_id = uuid.uuid4().hex[:8]
    file_path = str(settings.UPLOADS_DIR / f"{file_id}_{file.filename}")

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
    summary="[Step 2] 분석 실행 (JSON ,테스트 용)",
    description="업로드된 파일 경로와 JSON 설정을 받아 스윙 분석을 실행합니다."
)
async def analyze_json(
        request: AnalyzeRequest = Body(...),  # <--- Body를 통해 깔끔한 JSON으로 받음
        _authorized: bool = Depends(verify_api_key, use_cache=True)
):
    """
    테스트용 엔드포인트
    - Provider: 'noop' (비용 절감 강제)
    - Model: 요청 없으면 'gpt-4o-mini'
    """
    # 1) 파일 존재 여부 확인
    if not os.path.exists(request.file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File not found at path: {request.file_path}"
        )

    # LLM 설정 구성 (명시적 데이터 -> dict 변환)
    target_model = request.model_name or settings.LLM_DEFAULT_MODEL

    # Gateway로 보낼 데이터 구성
    llm_config = {
        "provider": settings.LLM_DEFAULT_PROVIDER or 'noop',
        "model": target_model,
        "user_id": request.user_id,
        "gateway_url": settings.LLM_GATEWAY_URL  # Service에서 사용할 URL
    }

    # 2) 분석 서비스 호출 (request 객체에서 값 사용)
    return analyze_swing(
        file_path=request.file_path,
        side=request.side.value,
        min_vis=request.min_vis,
        norm_mode=request.norm_mode,
        club=request.club,
        llm_config=llm_config
    )


@router.post(
    "",
    summary="[Main] 스윙 영상 분석 (Form-Data, 프로덕션용)",
    description="스윙 영상(file)과 메타데이터(llm_json)를 Form-Data로 받아 최종 리포트를 반환"
)
async def analyze(
        # API Key 검증
        _authorized: bool = Depends(verify_api_key, use_cache=True),

        file: UploadFile = File(..., description="분석할 스윙 영상"),
        side: SideEnum = Form(SideEnum.right, description="스윙 방향"),
        min_vis: float = Form(0.5, ge=0.0, le=1.0),
        norm_mode: NormMode = Form(NormMode.auto, description="전처리 모드"),
        club: Optional[ClubType] = Form(None, description="클럽 종류"),

        # [수정] Platform에서 전달받는 데이터
        user_id: str = Form(..., description="유저 아이디"),
        model_name: Optional[str] = Form(None, description="사용할 LLM 모델 (없으면 기본값)")
):
    # 1) 모델 결정
    target_model = model_name or settings.LLM_DEFAULT_MODEL

    # 2) LLM Config 구성
    llm_config = {
        "provider": settings.LLM_DEFAULT_PROVIDER,
        "model": target_model,
        "user_id": user_id,
        "gateway_url": settings.LLM_GATEWAY_URL
    }

    # 2) 파일 저장
    os.makedirs(settings.UPLOADS_DIR, exist_ok=True)
    file_id = uuid.uuid4().hex[:8]
    file_path = str(settings.UPLOADS_DIR / f"{file_id}_{file.filename}")

    # 3) LLM 파라미터 구성 (없으면 NOOP)
    try:
        with open(file_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"File could not be saved: {e}"
        )
    finally:
        file.file.close()

    # 4) 호출
    return analyze_swing(
        file_path=file_path,
        side=side.value,
        min_vis=min_vis,
        norm_mode=norm_mode,
        club=club,
        llm_config=llm_config
    )

ROUTER = [router]