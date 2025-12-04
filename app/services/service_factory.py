from app.config.settings import settings
from typing import Optional

from app.services.swing_analysis_service import SwingAnalysisService
from app.domain.video.preprocessor import VideoPreprocessor
from app.domain.pose.extractor import PoseExtractor
from app.domain.angle.calculator import AngleCalculator
from app.domain.phase.detector import PhaseDetector
from app.domain.diagnosis.engine import DiagnosisEngine
from app.infrastructure.llm.gateway_client import LLMGatewayClient
from app.infrastructure.storage.s3_client import S3StorageClient


def create_swing_analysis_service(
        club: str,
        swing_direction: str,
        visibility_threshold: float = 0.5,
        llm_provider: str = None,
        llm_model: Optional[str] = None
) -> SwingAnalysisService:
    """
    SwingAnalysisService 인스턴스 생성

    Args:
        club: 클럽 종류 (DiagnosisEngine에 전달)
        swing_direction: 스윙 방향 (PhaseDetector에 전달)
        visibility_threshold: MediaPipe 가시성 임계값
        llm_provider: LLM 제공자 (openai, anthropic)
        llm_model: LLM 모델명

    Returns:
        SwingAnalysisService 인스턴스
    """
    # Domain 컴포넌트 초기화
    video_preprocessor = VideoPreprocessor()
    pose_extractor = PoseExtractor(visibility_threshold=visibility_threshold)
    angle_calculator = AngleCalculator()
    phase_detector = PhaseDetector(swing_direction=swing_direction)
    diagnosis_engine = DiagnosisEngine(club=club)

    # Infrastructure 컴포넌트 초기화 (optional)
    llm_client = None
    if llm_provider in ("openai", "anthropic") and llm_model and settings.OPENAI_API_KEY:
        llm_client = LLMGatewayClient(
            gateway_url=settings.LLM_GATEWAY_URL,
            provider=llm_provider,
            model=llm_model,
            api_key=settings.OPENAI_API_KEY
        )

    storage_client = None
    if hasattr(settings, "S3_BUCKET_NAME") and settings.S3_BUCKET_NAME:
        storage_client = S3StorageClient(bucket_name=settings.S3_BUCKET_NAME)

    return SwingAnalysisService(
        video_preprocessor=video_preprocessor,
        pose_extractor=pose_extractor,
        angle_calculator=angle_calculator,
        phase_detector=phase_detector,
        diagnosis_engine=diagnosis_engine,
        llm_client=llm_client,
        storage_client=storage_client
    )