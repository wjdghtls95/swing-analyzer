"""
비디오 전처리 Domain Logic
외부 의존성 없는 순수 함수
"""
import cv2
import numpy as np

from app.schemas.video_dto import VideoPreprocessRequest, VideoPreprocessResult


class VideoPreprocessor:
    """비디오 전처리기 (표준화, 리샘플링)"""

    def process(self, request: VideoPreprocessRequest) -> tuple[list[np.ndarray], VideoPreprocessResult]:
        """
        비디오를 표준화하여 프레임 리스트로 반환

        Args:
            request: 전처리 요청 (경로, FPS, 높이 등)

        Returns:
            (frames, metadata)
            - frames: list[np.ndarray] (각 프레임 이미지)
            - metadata: VideoPreprocessResult (FPS, 해상도 등)
        """
        cap = cv2.VideoCapture(request.file_path)

        if not cap.isOpened():
            raise ValueError(f"Cannot open video: {request.file_path}")

        # 원본 비디오 정보
        original_fps = cap.get(cv2.CAP_PROP_FPS)
        original_frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        original_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        original_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        # 리샘플링 비율 계산
        frame_interval = int(original_fps / request.target_fps)
        if frame_interval < 1:
            frame_interval = 1

        # 타겟 해상도 계산
        scale_factor = request.target_height / original_height
        target_width = int(original_width * scale_factor)
        target_height = request.target_height

        frames = []
        frame_idx = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            # FPS 리샘플링 (N 프레임마다 1개 추출)
            if frame_idx % frame_interval == 0:
                # 리사이즈
                resized = cv2.resize(frame, (target_width, target_height))

                # 좌우 반전 (좌타자용)
                if request.mirror:
                    resized = cv2.flip(resized, 1)

                # RGB 변환 (MediaPipe는 RGB 사용)
                rgb_frame = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
                frames.append(rgb_frame)

            frame_idx += 1

        cap.release()

        # 메타데이터 생성
        actual_fps = request.target_fps
        duration = len(frames) / actual_fps

        metadata = VideoPreprocessResult(
            total_frames=len(frames),
            fps=actual_fps,
            duration=duration,
            width=target_width,
            height=target_height
        )

        return frames, metadata
