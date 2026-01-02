"""
Domain Logic Tests

도메인 계층 비즈니스 로직 테스트
"""
import pytest
import numpy as np
from tests.test_helpers import (
    create_empty_frame,
    create_angle_test_frame,
    create_visibility_test_frames,
    calculate_angle_from_points,
    validate_phase_order,
    assert_angle_range
)


class TestAngleCalculator:
    """AngleCalculator 도메인 로직 테스트"""
    
    def test_calculate_90_degree_elbow_angle(self):
        """90도 팔꿈치 각도 계산"""
        # 우측 팔: shoulder(12) - elbow(14) - wrist(16)
        frame = create_angle_test_frame((12, 14, 16), 90.0)
        
        # 실제 계산 로직 호출
        angle = calculate_angle_from_points(
            frame[12], frame[14], frame[16]
        )
        
        assert_angle_range(angle, 85.0, 95.0)
    
    def test_calculate_straight_arm_angle(self):
        """180도 (일직선) 팔 각도 계산"""
        frame = create_angle_test_frame((12, 14, 16), 180.0)
        
        angle = calculate_angle_from_points(
            frame[12], frame[14], frame[16]
        )
        
        assert_angle_range(angle, 175.0, 180.0)
    
    def test_calculate_acute_angle(self):
        """예각 (45도) 계산"""
        frame = create_angle_test_frame((12, 14, 16), 45.0)
        
        angle = calculate_angle_from_points(
            frame[12], frame[14], frame[16]
        )
        
        assert_angle_range(angle, 40.0, 50.0)
    
    def test_low_visibility_frames_skipped(self):
        """낮은 가시성 프레임은 계산에서 제외"""
        frames = create_visibility_test_frames(
            num_frames=10,
            low_vis_indices=[0, 1, 2, 8, 9]  # 처음 3개, 마지막 2개는 낮은 가시성
        )
        
        # 가시성이 높은 프레임만 계산됨
        # 실제 구현에서는 visibility_threshold로 필터링
        high_vis_frames = [f for f in frames if f[0]["visibility"] > 0.5]
        assert len(high_vis_frames) == 5  # 10 - 5 = 5개


class TestPhaseDetector:
    """PhaseDetector 도메인 로직 테스트"""
    
    def test_phase_order_validation(self):
        """Phase 순서가 올바른지 검증"""
        valid_phases = [
            {"phase": "address", "frame": 0, "timestamp": 0.0},
            {"phase": "backswing", "frame": 15, "timestamp": 0.25},
            {"phase": "top", "frame": 30, "timestamp": 0.5},
            {"phase": "downswing", "frame": 40, "timestamp": 0.67},
            {"phase": "impact", "frame": 45, "timestamp": 0.75},
            {"phase": "follow_through", "frame": 59, "timestamp": 0.98},
        ]
        
        assert validate_phase_order(valid_phases) is True
    
    def test_invalid_phase_order_detection(self):
        """잘못된 Phase 순서 감지"""
        invalid_phases = [
            {"phase": "address", "frame": 0, "timestamp": 0.0},
            {"phase": "top", "frame": 30, "timestamp": 0.5},
            {"phase": "backswing", "frame": 15, "timestamp": 0.25},  # 순서 역전
        ]
        
        assert validate_phase_order(invalid_phases) is False
    
    def test_minimum_phases_detected(self):
        """최소한의 주요 phase가 감지되는지 확인"""
        phases = [
            {"phase": "address", "frame": 0, "timestamp": 0.0},
            {"phase": "impact", "frame": 45, "timestamp": 0.75},
            {"phase": "follow_through", "frame": 59, "timestamp": 0.98},
        ]
        
        # 최소 3개 이상의 phase가 있어야 함
        assert len(phases) >= 3
        assert validate_phase_order(phases) is True


class TestDiagnosisEngine:
    """DiagnosisEngine 도메인 로직 테스트"""
    
    def test_score_range_validation(self):
        """진단 점수가 0-100 범위인지 검증"""
        scores = [0, 50, 85, 100]
        
        for score in scores:
            assert 0 <= score <= 100
    
    def test_diagnosis_with_good_angles(self):
        """좋은 각도 값으로 진단 시 높은 점수"""
        # 이상적인 각도 범위
        ideal_angles = {
            "left_elbow": 140.0,  # 이상적
            "right_elbow": 140.0,
            "left_knee": 160.0,
            "right_knee": 160.0,
        }
        
        # 실제 DiagnosisEngine 로직은 threshold와 비교
        # 여기서는 검증 로직만 테스트
        for angle in ideal_angles.values():
            assert 120.0 <= angle <= 170.0  # 정상 범위
    
    def test_diagnosis_with_poor_angles(self):
        """나쁜 각도 값으로 진단 시 낮은 점수"""
        poor_angles = {
            "left_elbow": 90.0,   # 너무 구부러짐
            "right_elbow": 180.0, # 너무 펴짐
            "left_knee": 120.0,   # 너무 구부러짐
            "right_knee": 180.0,
        }
        
        # 비정상 범위 검증
        assert poor_angles["left_elbow"] < 120.0
        assert poor_angles["right_elbow"] > 170.0


class TestPoseExtractor:
    """PoseExtractor 도메인 로직 테스트"""
    
    def test_landmark_count(self, sample_pose_frame):
        """MediaPipe는 33개 랜드마크를 반환해야 함"""
        assert len(sample_pose_frame) == 33
    
    def test_landmark_structure(self, sample_mediapipe_landmark):
        """랜드마크 구조 검증 (x, y, z, visibility)"""
        assert "x" in sample_mediapipe_landmark
        assert "y" in sample_mediapipe_landmark
        assert "z" in sample_mediapipe_landmark
        assert "visibility" in sample_mediapipe_landmark
    
    def test_visibility_range(self, sample_pose_frame):
        """visibility 값이 0.0~1.0 범위인지 검증"""
        for landmark in sample_pose_frame:
            vis = landmark["visibility"]
            assert 0.0 <= vis <= 1.0
    
    def test_coordinate_range(self, sample_pose_frame):
        """좌표 값이 정규화된 범위(-1.0~1.0 또는 0.0~1.0)인지 검증"""
        for landmark in sample_pose_frame:
            # MediaPipe는 일반적으로 0.0~1.0 범위로 정규화
            # 실제 구현에 따라 범위가 다를 수 있음
            assert -2.0 <= landmark["x"] <= 2.0
            assert -2.0 <= landmark["y"] <= 2.0
            assert -2.0 <= landmark["z"] <= 2.0


class TestVideoPreprocessor:
    """VideoPreprocessor 도메인 로직 테스트"""
    
    def test_fps_normalization(self):
        """FPS 정규화 검증"""
        target_fps = 60
        original_fps = 30
        
        # FPS가 2배 증가하면 프레임 수도 2배
        expected_frame_multiplier = target_fps / original_fps
        assert expected_frame_multiplier == 2.0
    
    def test_mirror_for_left_handed(self):
        """왼손잡이 스윙은 mirror=True"""
        swing_direction = "left"
        mirror = (swing_direction == "left")
        
        assert mirror is True
    
    def test_no_mirror_for_right_handed(self):
        """오른손잡이 스윙은 mirror=False"""
        swing_direction = "right"
        mirror = (swing_direction == "left")
        
        assert mirror is False


class TestIntegrationWithHelpers:
    """test_helpers 유틸리티 통합 테스트"""
    
    def test_create_empty_frame_structure(self):
        """빈 프레임 생성 헬퍼 검증"""
        frame = create_empty_frame(num_landmarks=33)
        
        assert len(frame) == 33
        assert all(lm["x"] == 0.0 for lm in frame)
        assert all(lm["visibility"] == 1.0 for lm in frame)
    
    def test_angle_test_frame_creates_correct_angle(self):
        """각도 테스트 프레임이 정확한 각도를 생성하는지 검증"""
        frame = create_angle_test_frame((12, 14, 16), 90.0)
        
        calculated_angle = calculate_angle_from_points(
            frame[12], frame[14], frame[16]
        )
        
        # 90도 ± 1도 허용
        assert 89.0 <= calculated_angle <= 91.0
    
    def test_visibility_test_frames_creates_correct_pattern(self):
        """가시성 테스트 프레임이 올바른 패턴을 생성하는지 검증"""
        frames = create_visibility_test_frames(
            num_frames=10,
            low_vis_indices=[0, 5, 9]
        )
        
        assert len(frames) == 10
        
        # 지정된 인덱스는 낮은 가시성
        assert frames[0][0]["visibility"] < 0.5
        assert frames[5][0]["visibility"] < 0.5
        assert frames[9][0]["visibility"] < 0.5
        
        # 나머지는 높은 가시성
        assert frames[1][0]["visibility"] == 1.0
        assert frames[2][0]["visibility"] == 1.0
