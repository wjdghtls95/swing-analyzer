"""
스윙 분석 Service Layer
Domain 컴포넌트들을 조합하여 전체 분석 파이프라인 실행
"""
import uuid
from datetime import datetime
from typing import Optional

from app.schemas.analyze_dto import (
    AnalyzeSwingRequest,
    AnalyzeSwingResponse,
    PhaseResult,
    DiagnosisResult as ApiDiagnosisResult
)
from app.schemas.video_dto import VideoPreprocessRequest
from app.domain.video.preprocessor import VideoPreprocessor
from app.domain.pose.extractor import PoseExtractor
from app.domain.angle.calculator import AngleCalculator
from app.domain.phase.detector import PhaseDetector
from app.domain.diagnosis.engine import DiagnosisEngine
from app.infrastructure.llm.gateway_client import LLMGatewayClient
from app.infrastructure.storage.s3_client import S3StorageClient


class SwingAnalysisService:
    """
    스윙 분석 메인 서비스

    책임:
    - 전체 분석 파이프라인 오케스트레이션
    - Domain 컴포넌트 간 데이터 흐름 관리
    - 외부 인프라(LLM, S3) 호출
    """

    def __init__(
        self,
        video_preprocessor: VideoPreprocessor,
        pose_extractor: PoseExtractor,
        angle_calculator: AngleCalculator,
        phase_detector: PhaseDetector,
        diagnosis_engine: DiagnosisEngine,
        llm_client: Optional[LLMGatewayClient] = None,
        storage_client: Optional[S3StorageClient] = None
    ):
        """
        Args:
            video_preprocessor: 비디오 전처리기
            pose_extractor: 포즈 추출기
            angle_calculator: 각도 계산기
            phase_detector: 페이즈 감지기
            diagnosis_engine: 진단 엔진
            llm_client: LLM 클라이언트 (선택적)
            storage_client: S3 클라이언트 (선택적)
        """
        self.video_preprocessor = video_preprocessor
        self.pose_extractor = pose_extractor
        self.angle_calculator = angle_calculator
        self.phase_detector = phase_detector
        self.diagnosis_engine = diagnosis_engine
        self.llm_client = llm_client
        self.storage_client = storage_client

    async def analyze(self, request: AnalyzeSwingRequest) -> AnalyzeSwingResponse:
        """
        스윙 분석 파이프라인 실행

        Process:
        1. 비디오 전처리
        2. 포즈 추출
        3. 각도 계산
        4. 페이즈 감지
        5. 진단 생성
        6. AI 피드백 생성
        7. S3 저장 (선택적)

        Args:
            request: 분석 요청 DTO

        Returns:
            AnalyzeSwingResponse
        """
        analysis_id = self._generate_analysis_id()

        # ========== Step 1: 비디오 전처리 ==========
        preprocess_request = VideoPreprocessRequest(
            file_path=request.file_path,
            target_fps=60,  # settings에서 가져올 수도 있음
            target_height=720,
            mirror=(request.swing_direction == "left")
        )
        frames, video_metadata = self.video_preprocessor.process(preprocess_request)

        # ========== Step 2: 포즈 추출 ==========
        pose_result = self.pose_extractor.extract(frames, video_metadata.fps)

        # ========== Step 3: 각도 계산 ==========
        angle_result = self.angle_calculator.calculate(pose_result.poses)

        # ========== Step 4: 페이즈 감지 ==========
        phase_result = self.phase_detector.detect(
            poses=pose_result.poses,
            angles=angle_result.angles,
            fps=video_metadata.fps
        )

        # ========== Step 5: 진단 생성 ==========
        diagnosis_result = self.diagnosis_engine.diagnose(phase_result.phases)

        # ========== Step 6: AI 피드백 생성 (선택적) ==========
        ai_feedback = ""
        if self.llm_client:
            ai_feedback = self.llm_client.generate_feedback(
                diagnosis=diagnosis_result,
                user_id=request.user_id,
                club=request.club,
                tone="professional",
                language="ko"
            )
        else:
            # Fallback: 진단 텍스트만 반환
            ai_feedback = self._generate_text_feedback(diagnosis_result)

        # ========== Step 7: Response DTO 생성 ==========
        response = AnalyzeSwingResponse(
            analysis_id=analysis_id,
            user_id=request.user_id,
            club=request.club,
            phases=[
                PhaseResult(
                    name=phase.name,
                    start_frame=phase.start_frame,
                    end_frame=phase.end_frame,
                    timestamp_start=phase.start_time,
                    timestamp_end=phase.end_time,
                    key_angles=phase.representative_angles
                )
                for phase in phase_result.phases
            ],
            diagnosis_by_phase=[
                ApiDiagnosisResult(
                    phase=d.phase,
                    score=d.score,
                    issues=d.issues,
                    suggestions=d.suggestions
                )
                for d in diagnosis_result.diagnoses
            ],
            overall_score=diagnosis_result.overall_score,
            ai_feedback=ai_feedback,
            result_url=None  # S3 업로드 후 업데이트
        )

        # ========== Step 8: S3 저장 (선택적) ==========
        if self.storage_client:
            result_url = self.storage_client.upload_result(response)
            response.result_url = result_url

        return response

    def _generate_analysis_id(self) -> str:
        """분석 ID 생성 (UUID + timestamp)"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        return f"analysis_{timestamp}_{unique_id}"

    def _generate_text_feedback(self, diagnosis_result) -> str:
        """LLM 없을 때 텍스트 피드백"""
        lines = [f"전체 점수: {diagnosis_result.overall_score:.1f}/100\n"]

        for d in diagnosis_result.diagnoses:
            if d.score < 80:  # 80점 미만만 표시
                lines.append(f"[{d.phase}] {d.score:.1f}점")
                if d.issues:
                    lines.append(f"  문제: {d.issues[0]}")
                if d.suggestions:
                    lines.append(f"  개선: {d.suggestions[0]}")

        return "\n".join(lines)
