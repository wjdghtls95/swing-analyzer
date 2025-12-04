"""
페이즈 감지 관련 DTO
PhaseDetector 입출력용
"""
from pydantic import BaseModel, Field
from typing import Literal

PhaseType = Literal["Address", "Backswing", "Top", "Downswing", "Impact", "Follow-through"]

class PhaseInfo(BaseModel):
    """1개 페이즈 정보"""
    name: PhaseType
    start_frame: int
    end_frame: int
    start_time: float
    end_time: float
    duration: float = Field(..., description="페이즈 지속 시간(초)")

    # 이 페이즈의 대표 각도 (평균값)
    representative_angles: dict = Field(
        ...,
        description="이 페이즈의 평균 각도",
        example={"left_elbow": 145.2, "right_knee": 125.8}
    )


class PhaseDetectionResult(BaseModel):
    """페이즈 감지 결과 (6단계)"""
    phases: list[PhaseInfo] = Field(..., min_items=6, max_items=6)

    def get_phase(self, phase_name: PhaseType) -> PhaseInfo:
        """특정 페이즈 정보 반환"""
        for phase in self.phases:
            if phase.name == phase_name:
                return phase
        raise ValueError(f"Phase {phase_name} not found")
