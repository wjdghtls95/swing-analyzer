"""
각도 계산 관련 DTO
AngleCalculator 입출력용
"""
from pydantic import BaseModel, Field

class AngleMetrics(BaseModel):
    """1개 프레임의 각도 측정값"""
    frame_number: int
    timestamp: float

    # 팔꿈치 각도
    left_elbow: float = Field(..., description="왼쪽 팔꿈치 각도 (도)")
    right_elbow: float = Field(..., description="오른쪽 팔꿈치 각도 (도)")

    # 무릎 각도
    left_knee: float = Field(..., description="왼쪽 무릎 각도 (도)")
    right_knee: float = Field(..., description="오른쪽 무릎 각도 (도)")

    # 엉덩이 각도
    left_hip: float = Field(..., description="왼쪽 엉덩이 각도 (도)")
    right_hip: float = Field(..., description="오른쪽 엉덩이 각도 (도)")

    # X-Factor (어깨-엉덩이 회전 차이)
    x_factor: float = Field(..., description="X-Factor (도)")

    # 어깨 회전 각도
    shoulder_rotation: float = Field(..., description="어깨 회전 각도 (도)")
    hip_rotation: float = Field(..., description="엉덩이 회전 각도 (도)")


class AngleCalculationResult(BaseModel):
    """전체 비디오의 각도 계산 결과"""
    total_frames: int
    angles: list[AngleMetrics] = Field(..., description="프레임별 각도 측정값")

    # 평균값 (진단에 사용)
    avg_left_elbow: float
    avg_right_elbow: float
    avg_left_knee: float
    avg_right_knee: float
    avg_x_factor: float
