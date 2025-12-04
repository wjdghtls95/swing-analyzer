"""
비디오 전처리 관련 DTO
VideoPreprocessor 입출력용
"""
from pydantic import BaseModel, Field

class VideoPreprocessRequest(BaseModel):
    """비디오 전처리 요청"""
    file_path: str
    target_fps: int = Field(default=60, ge=1, description="목표 FPS")
    target_height: int = Field(default=720, ge=480, description="목표 높이(px)")
    mirror: bool = Field(default=False, description="좌우 반전 여부")

    class Config:
        # NumPy 배열 직렬화 문제 방지
        arbitrary_types_allowed = True


class VideoFrame(BaseModel):
    """개별 프레임 데이터"""
    frame_number: int
    timestamp: float  # 초 단위
    # image: np.ndarray  # Pydantic은 numpy 직렬화 안되므로 서비스 내부에서만 사용
    width: int
    height: int

    class Config:
        arbitrary_types_allowed = True


class VideoPreprocessResult(BaseModel):
    """비디오 전처리 결과"""
    total_frames: int
    fps: float
    duration: float  # 초
    width: int
    height: int
    # frames는 실제로는 list[np.ndarray]지만 DTO에는 메타데이터만

    class Config:
        arbitrary_types_allowed = True
