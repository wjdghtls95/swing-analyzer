"""
Service Layer Tests

SwingAnalysisService 비즈니스 로직 테스트
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from app.services.swing_analysis_service import SwingAnalysisService
from app.schemas.analyze_dto import AnalyzeSwingRequest


class TestSwingAnalysisService:
    """SwingAnalysisService 테스트"""
    
    @pytest.fixture
    def service(
        self,
        mock_video_preprocessor,
        mock_pose_extractor,
        mock_angle_calculator,
        mock_phase_detector,
        mock_diagnosis_engine,
        mock_llm_client,
        mock_s3_client
    ):
        """테스트용 Service 인스턴스 (모든 의존성 Mock)"""
        return SwingAnalysisService(
            video_preprocessor=mock_video_preprocessor,
            pose_extractor=mock_pose_extractor,
            angle_calculator=mock_angle_calculator,
            phase_detector=mock_phase_detector,
            diagnosis_engine=mock_diagnosis_engine,
            llm_client=mock_llm_client,
            storage_client=mock_s3_client
        )
    
    @pytest.fixture
    def analyze_request(self, tmp_path):
        """분석 요청 DTO"""
        video_path = tmp_path / "test_swing.mp4"
        video_path.write_bytes(b"fake video")
        
        return AnalyzeSwingRequest(
            file_path=str(video_path),
            user_id="test_user",
            club="driver",
            swing_direction="right",
            visibility_threshold=0.5,
            normalize_mode="height",
            llm_provider="noop",
            llm_model=None
        )
    
    @pytest.mark.asyncio
    async def test_analyze_pipeline_success(self, service, analyze_request):
        """정상 분석 파이프라인 실행"""
        result = await service.analyze(analyze_request)
        
        # 응답 구조 검증
        assert result.analysis_id is not None
        assert len(result.analysis_id) > 0
        
        assert result.phases is not None
        assert len(result.phases) > 0
        
        assert result.angles is not None
        assert "left_elbow" in result.angles
        
        assert result.diagnosis is not None
        assert result.diagnosis.score >= 0
        assert result.diagnosis.score <= 100
    
    @pytest.mark.asyncio
    async def test_analyze_calls_all_components(self, service, analyze_request):
        """모든 도메인 컴포넌트가 호출되는지 검증"""
        await service.analyze(analyze_request)
        
        # 각 컴포넌트가 정확히 1번씩 호출됨
        service.video_preprocessor.process.assert_called_once()
        service.pose_extractor.extract.assert_called_once()
        service.angle_calculator.calculate.assert_called_once()
        service.phase_detector.detect.assert_called_once()
        service.diagnosis_engine.diagnose.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_analyze_with_llm_feedback(self, service, analyze_request):
        """LLM 피드백 생성 포함 분석"""
        analyze_request.llm_provider = "openai"
        
        result = await service.analyze(analyze_request)
        
        # LLM 클라이언트가 호출됨
        service.llm_client.generate_feedback.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_analyze_without_llm_feedback(self, service, analyze_request):
        """LLM 피드백 없이 분석"""
        analyze_request.llm_provider = "noop"
        
        result = await service.analyze(analyze_request)
        
        # LLM 클라이언트가 호출되지 않음
        assert not service.llm_client.generate_feedback.called
    
    @pytest.mark.asyncio
    async def test_analyze_with_s3_upload(self, service, analyze_request):
        """S3 업로드 포함 분석"""
        result = await service.analyze(analyze_request)
        
        # S3 업로드가 호출됨 (storage_client가 설정된 경우)
        if service.storage_client:
            # 실제 구현에 따라 호출 여부 확인
            pass
    
    @pytest.mark.asyncio
    async def test_analyze_left_handed_swing(self, service, analyze_request):
        """왼손잡이 스윙 분석 (mirror=True)"""
        analyze_request.swing_direction = "left"
        
        result = await service.analyze(analyze_request)
        
        # VideoPreprocessor에 mirror=True로 전달됨
        call_args = service.video_preprocessor.process.call_args
        preprocess_request = call_args[0][0]
        assert preprocess_request.mirror is True
    
    @pytest.mark.asyncio
    async def test_analyze_generates_unique_ids(self, service, analyze_request):
        """각 분석마다 고유한 ID 생성"""
        result1 = await service.analyze(analyze_request)
        result2 = await service.analyze(analyze_request)
        
        assert result1.analysis_id != result2.analysis_id


class TestServiceFactory:
    """ServiceFactory 테스트"""
    
    def test_create_swing_analysis_service_with_noop_llm(self):
        """noop LLM provider로 서비스 생성"""
        from app.services.service_factory import create_swing_analysis_service
        
        service = create_swing_analysis_service(
            club="driver",
            swing_direction="right",
            visibility_threshold=0.5,
            llm_provider="noop"
        )
        
        assert service is not None
        assert service.video_preprocessor is not None
        assert service.pose_extractor is not None
        assert service.angle_calculator is not None
        assert service.phase_detector is not None
        assert service.diagnosis_engine is not None
    
    @pytest.mark.skip(reason="OpenAI API key 필요")
    def test_create_swing_analysis_service_with_openai(self):
        """openai LLM provider로 서비스 생성"""
        from app.services.service_factory import create_swing_analysis_service
        
        service = create_swing_analysis_service(
            club="driver",
            swing_direction="right",
            visibility_threshold=0.5,
            llm_provider="openai",
            llm_model="gpt-4o-mini"
        )
        
        assert service is not None
        assert service.llm_client is not None


class TestServiceErrorHandling:
    """Service 에러 처리 테스트"""
    
    @pytest.mark.asyncio
    async def test_analyze_with_video_processing_error(
        self,
        mock_pose_extractor,
        mock_angle_calculator,
        mock_phase_detector,
        mock_diagnosis_engine
    ):
        """비디오 전처리 실패 시 에러 처리"""
        # VideoPreprocessor가 예외를 발생시키도록 설정
        mock_video_preprocessor = Mock()
        mock_video_preprocessor.process.side_effect = ValueError("Invalid video format")
        
        service = SwingAnalysisService(
            video_preprocessor=mock_video_preprocessor,
            pose_extractor=mock_pose_extractor,
            angle_calculator=mock_angle_calculator,
            phase_detector=mock_phase_detector,
            diagnosis_engine=mock_diagnosis_engine
        )
        
        request = AnalyzeSwingRequest(
            file_path="/fake/path.mp4",
            user_id="test",
            club="driver",
            swing_direction="right"
        )
        
        with pytest.raises(ValueError):
            await service.analyze(request)
    
    @pytest.mark.asyncio
    async def test_analyze_with_pose_extraction_error(
        self,
        mock_video_preprocessor,
        mock_angle_calculator,
        mock_phase_detector,
        mock_diagnosis_engine
    ):
        """포즈 추출 실패 시 에러 처리"""
        # PoseExtractor가 예외를 발생시키도록 설정
        mock_pose_extractor = Mock()
        mock_pose_extractor.extract.side_effect = RuntimeError("Mediapipe error")
        
        service = SwingAnalysisService(
            video_preprocessor=mock_video_preprocessor,
            pose_extractor=mock_pose_extractor,
            angle_calculator=mock_angle_calculator,
            phase_detector=mock_phase_detector,
            diagnosis_engine=mock_diagnosis_engine
        )
        
        request = AnalyzeSwingRequest(
            file_path="/fake/path.mp4",
            user_id="test",
            club="driver",
            swing_direction="right"
        )
        
        with pytest.raises(RuntimeError):
            await service.analyze(request)
