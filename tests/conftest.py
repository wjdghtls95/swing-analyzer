"""
Pytest Configuration & Shared Fixtures

이 파일은 모든 테스트에서 재사용 가능한 fixture를 정의합니다.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, MagicMock
import numpy as np
from typing import List, Dict, Any


# ========================================
# Application Fixtures
# ========================================

@pytest.fixture(scope="session")
def app():
    """FastAPI 애플리케이션 인스턴스"""
    from app.main import app as fastapi_app
    return fastapi_app


@pytest.fixture(scope="session")
def client(app):
    """FastAPI TestClient (API 테스트용)"""
    return TestClient(app)


@pytest.fixture
def auth_headers():
    """인증 헤더 (X-Internal-Api-Key)"""
    return {"X-Internal-Api-Key": "test-api-key"}


# ========================================
# Domain Object Fixtures
# ========================================

@pytest.fixture
def sample_mediapipe_landmark() -> Dict[str, float]:
    """단일 MediaPipe 랜드마크"""
    return {
        "x": 0.5,
        "y": 0.5,
        "z": 0.0,
        "visibility": 1.0
    }


@pytest.fixture
def sample_pose_frame() -> List[Dict[str, float]]:
    """MediaPipe 33개 랜드마크 프레임 (정상 가시성)"""
    return [
        {
            "x": 0.5,
            "y": 0.5 + i * 0.01,  # 약간씩 다른 위치
            "z": 0.0,
            "visibility": 1.0
        }
        for i in range(33)
    ]


@pytest.fixture
def sample_pose_sequence(sample_pose_frame) -> List[List[Dict[str, float]]]:
    """포즈 프레임 시퀀스 (10프레임)"""
    return [sample_pose_frame.copy() for _ in range(10)]


@pytest.fixture
def low_visibility_frame(sample_pose_frame) -> List[Dict[str, float]]:
    """가시성이 낮은 프레임 (테스트용)"""
    frame = sample_pose_frame.copy()
    for landmark in frame:
        landmark["visibility"] = 0.3
    return frame


# ========================================
# Mock Service Fixtures
# ========================================

@pytest.fixture
def mock_video_preprocessor():
    """Mock VideoPreprocessor"""
    mock = Mock()
    mock.process.return_value = (
        np.random.rand(60, 720, 1280, 3),  # 60 frames
        Mock(fps=60, width=1280, height=720, total_frames=60)
    )
    return mock


@pytest.fixture
def mock_pose_extractor():
    """Mock PoseExtractor"""
    mock = Mock()
    mock.extract.return_value = Mock(
        poses=[
            [{"x": 0.5, "y": 0.5, "z": 0.0, "visibility": 1.0} for _ in range(33)]
            for _ in range(60)
        ],
        fps=60
    )
    return mock


@pytest.fixture
def mock_angle_calculator():
    """Mock AngleCalculator"""
    mock = Mock()
    mock.calculate.return_value = Mock(
        angles={
            "left_elbow": [140.0] * 60,
            "right_elbow": [140.0] * 60,
            "left_knee": [160.0] * 60,
            "right_knee": [160.0] * 60,
        }
    )
    return mock


@pytest.fixture
def mock_phase_detector():
    """Mock PhaseDetector"""
    mock = Mock()
    mock.detect.return_value = Mock(
        phases=[
            {"phase": "address", "frame": 0, "timestamp": 0.0},
            {"phase": "backswing", "frame": 15, "timestamp": 0.25},
            {"phase": "top", "frame": 30, "timestamp": 0.5},
            {"phase": "downswing", "frame": 40, "timestamp": 0.67},
            {"phase": "impact", "frame": 45, "timestamp": 0.75},
            {"phase": "follow_through", "frame": 59, "timestamp": 0.98},
        ]
    )
    return mock


@pytest.fixture
def mock_diagnosis_engine():
    """Mock DiagnosisEngine"""
    mock = Mock()
    mock.diagnose.return_value = Mock(
        score=85,
        issues=["백스윙 속도 약간 느림"],
        suggestions=["임팩트 순간 왼쪽 무릎 각도 유지"]
    )
    return mock


@pytest.fixture
def mock_llm_client():
    """Mock LLMGatewayClient"""
    mock = Mock()
    mock.generate_feedback.return_value = "전반적으로 좋은 스윙입니다. 백스윙 속도를 조금 더 높이세요."
    return mock


@pytest.fixture
def mock_s3_client():
    """Mock S3StorageClient"""
    mock = Mock()
    mock.upload.return_value = "https://s3.amazonaws.com/bucket/video.mp4"
    return mock


# ========================================
# Sample Data Fixtures
# ========================================

@pytest.fixture
def sample_analyze_request():
    """분석 요청 샘플 데이터"""
    return {
        "user_id": "test_user_123",
        "club": "driver",
        "swing_direction": "right",
        "visibility_threshold": 0.5,
        "normalize_mode": "height",
        "llm_provider": "noop",
        "llm_model": None
    }


@pytest.fixture
def sample_video_file(tmp_path):
    """임시 비디오 파일 (빈 파일)"""
    video_path = tmp_path / "sample_swing.mp4"
    video_path.write_bytes(b"fake video content")
    return video_path


# ========================================
# Utility Functions
# ========================================

@pytest.fixture
def assert_valid_angle():
    """각도 값 유효성 검증 헬퍼"""
    def _assert(angle: float, min_val: float = 0.0, max_val: float = 180.0):
        assert not np.isnan(angle), "Angle should not be NaN"
        assert min_val <= angle <= max_val, f"Angle {angle} out of range [{min_val}, {max_val}]"
    return _assert


@pytest.fixture
def assert_valid_phase_sequence():
    """Phase 시퀀스 유효성 검증 헬퍼"""
    def _assert(phases: List[Dict[str, Any]]):
        expected_order = ["address", "backswing", "top", "downswing", "impact", "follow_through"]
        phase_names = [p["phase"] for p in phases]
        
        # 최소 3개 이상의 phase가 감지되어야 함
        assert len(phases) >= 3, f"Too few phases detected: {len(phases)}"
        
        # Phase 순서가 단조 증가해야 함
        for i in range(len(phases) - 1):
            assert phases[i]["frame"] < phases[i + 1]["frame"], "Phase frames must be monotonically increasing"
            
    return _assert
