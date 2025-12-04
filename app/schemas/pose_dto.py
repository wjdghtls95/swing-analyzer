"""
포즈 추출 관련 DTO
PoseExtractor 입출력용
"""
from pydantic import BaseModel, Field
from typing import Optional

class Keypoint(BaseModel):
    """MediaPipe 포즈 keypoint (33개 중 하나)"""
    x: float = Field(..., ge=0.0, le=1.0, description="정규화된 X 좌표 (0~1)")
    y: float = Field(..., ge=0.0, le=1.0, description="정규화된 Y 좌표 (0~1)")
    z: float = Field(..., description="깊이 (상대적)")
    visibility: float = Field(..., ge=0.0, le=1.0, description="가시성 점수")


class PoseData(BaseModel):
    """1개 프레임의 포즈 데이터 (33개 keypoints)"""
    frame_number: int
    timestamp: float

    # MediaPipe 33 keypoints (일부만 예시)
    nose: Keypoint
    left_shoulder: Keypoint
    right_shoulder: Keypoint
    left_elbow: Keypoint
    right_elbow: Keypoint
    left_wrist: Keypoint
    right_wrist: Keypoint
    left_hip: Keypoint
    right_hip: Keypoint
    left_knee: Keypoint
    right_knee: Keypoint
    left_ankle: Keypoint
    right_ankle: Keypoint
    # ... (실제로는 33개 전부)

    def get_keypoint(self, name: str) -> Optional[Keypoint]:
        """keypoint 이름으로 접근"""
        return getattr(self, name, None)


class PoseExtractionResult(BaseModel):
    """전체 비디오의 포즈 추출 결과"""
    total_frames: int
    poses: list[PoseData] = Field(..., description="프레임별 포즈 데이터")

    def get_pose_at_frame(self, frame_num: int) -> Optional[PoseData]:
        """특정 프레임의 포즈 반환"""
        for pose in self.poses:
            if pose.frame_number == frame_num:
                return pose
        return None
