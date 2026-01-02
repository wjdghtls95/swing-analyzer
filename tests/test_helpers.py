"""
Test Helper Utilities

재사용 가능한 테스트 헬퍼 함수들을 모아놓은 모듈입니다.
"""
from typing import List, Dict, Any
import numpy as np


# ========================================
# Pose Data Generators
# ========================================

def create_empty_frame(num_landmarks: int = 33) -> List[Dict[str, float]]:
    """
    빈 포즈 프레임 생성 (모든 랜드마크가 원점)
    
    Args:
        num_landmarks: 랜드마크 개수 (기본 33개)
        
    Returns:
        List[Dict]: MediaPipe 랜드마크 리스트
    """
    return [
        {"x": 0.0, "y": 0.0, "z": 0.0, "visibility": 1.0}
        for _ in range(num_landmarks)
    ]


def create_angle_test_frame(
    landmark_ids: tuple[int, int, int],
    angle_degree: float
) -> List[Dict[str, float]]:
    """
    특정 각도를 만드는 테스트 프레임 생성
    
    Args:
        landmark_ids: (point_a, vertex, point_b) 인덱스
        angle_degree: 목표 각도 (degree)
        
    Returns:
        List[Dict]: 해당 각도를 만드는 프레임
        
    Example:
        >>> frame = create_angle_test_frame((12, 14, 16), 90.0)  # 90도 팔꿈치 각도
    """
    frame = create_empty_frame()
    
    a, vertex, b = landmark_ids
    angle_rad = np.radians(angle_degree)
    
    # Vertex를 원점에 배치
    frame[vertex] = {"x": 0.0, "y": 0.0, "z": 0.0, "visibility": 1.0}
    
    # Point A를 (1, 0, 0)에 배치
    frame[a] = {"x": 1.0, "y": 0.0, "z": 0.0, "visibility": 1.0}
    
    # Point B를 각도에 맞게 배치
    frame[b] = {
        "x": np.cos(angle_rad),
        "y": np.sin(angle_rad),
        "z": 0.0,
        "visibility": 1.0
    }
    
    return frame


def create_visibility_test_frames(
    num_frames: int = 10,
    low_vis_indices: List[int] = None
) -> List[List[Dict[str, float]]]:
    """
    가시성 테스트용 프레임 시퀀스 생성
    
    Args:
        num_frames: 전체 프레임 수
        low_vis_indices: 낮은 가시성을 가질 프레임 인덱스 리스트
        
    Returns:
        List[List[Dict]]: 프레임 시퀀스
    """
    low_vis_indices = low_vis_indices or []
    frames = []
    
    for i in range(num_frames):
        frame = create_empty_frame()
        
        if i in low_vis_indices:
            # 낮은 가시성
            for landmark in frame:
                landmark["visibility"] = 0.2
        
        frames.append(frame)
    
    return frames


# ========================================
# Angle Calculation Helpers
# ========================================

def calculate_angle_from_points(
    point_a: Dict[str, float],
    vertex: Dict[str, float],
    point_b: Dict[str, float]
) -> float:
    """
    3개 점으로 각도 계산 (검증용)
    
    Args:
        point_a: 첫 번째 점
        vertex: 꼭지점
        point_b: 세 번째 점
        
    Returns:
        float: 각도 (degree)
    """
    # 벡터 생성
    ba = np.array([point_a["x"] - vertex["x"], 
                   point_a["y"] - vertex["y"], 
                   point_a["z"] - vertex["z"]])
    bc = np.array([point_b["x"] - vertex["x"], 
                   point_b["y"] - vertex["y"], 
                   point_b["z"] - vertex["z"]])
    
    # 코사인 값 계산
    cosine = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc))
    angle_rad = np.arccos(np.clip(cosine, -1.0, 1.0))
    
    return np.degrees(angle_rad)


# ========================================
# Phase Validation Helpers
# ========================================

def validate_phase_order(phases: List[Dict[str, Any]]) -> bool:
    """
    Phase 순서가 올바른지 검증
    
    Args:
        phases: Phase 리스트
        
    Returns:
        bool: 순서가 올바르면 True
    """
    if len(phases) < 2:
        return True
    
    for i in range(len(phases) - 1):
        current_frame = phases[i]["frame"]
        next_frame = phases[i + 1]["frame"]
        
        if current_frame >= next_frame:
            return False
    
    return True


def get_phase_duration(phases: List[Dict[str, Any]], phase_name: str) -> float:
    """
    특정 phase의 지속 시간 계산
    
    Args:
        phases: Phase 리스트
        phase_name: Phase 이름
        
    Returns:
        float: 지속 시간 (초), 없으면 0.0
    """
    phase_indices = [i for i, p in enumerate(phases) if p["phase"] == phase_name]
    
    if not phase_indices:
        return 0.0
    
    idx = phase_indices[0]
    
    if idx + 1 < len(phases):
        return phases[idx + 1]["timestamp"] - phases[idx]["timestamp"]
    
    return 0.0


# ========================================
# Mock Response Builders
# ========================================

def build_mock_analysis_response(
    analysis_id: str = "test_analysis_123",
    score: int = 85,
    num_phases: int = 6
) -> Dict[str, Any]:
    """
    Mock 분석 응답 생성
    
    Args:
        analysis_id: 분석 ID
        score: 진단 점수
        num_phases: Phase 개수
        
    Returns:
        Dict: 분석 응답 데이터
    """
    phase_names = ["address", "backswing", "top", "downswing", "impact", "follow_through"]
    
    return {
        "analysis_id": analysis_id,
        "phases": [
            {
                "phase": phase_names[i],
                "frame": i * 10,
                "timestamp": i * 0.167
            }
            for i in range(num_phases)
        ],
        "angles": {
            "left_elbow": [140.0] * 60,
            "right_elbow": [140.0] * 60,
            "left_knee": [160.0] * 60,
            "right_knee": [160.0] * 60,
        },
        "diagnosis": {
            "score": score,
            "issues": ["테스트 이슈"],
            "suggestions": ["테스트 제안"]
        },
        "created_at": "2026-01-02T08:00:00Z"
    }


# ========================================
# Assertion Helpers
# ========================================

def assert_response_structure(response: Dict[str, Any], required_keys: List[str]):
    """
    응답 구조 검증
    
    Args:
        response: 응답 딕셔너리
        required_keys: 필수 키 리스트
    """
    for key in required_keys:
        assert key in response, f"Missing required key: {key}"


def assert_angle_range(angle: float, min_val: float = 0.0, max_val: float = 180.0):
    """
    각도 범위 검증
    
    Args:
        angle: 각도 값
        min_val: 최소값
        max_val: 최대값
    """
    assert not np.isnan(angle), "Angle should not be NaN"
    assert not np.isinf(angle), "Angle should not be infinite"
    assert min_val <= angle <= max_val, f"Angle {angle} out of range [{min_val}, {max_val}]"
