"""
왜 이 모듈이 필요한가?
- 원본 동영상에서 프레임을 샘플링(step 간격)하며 MediaPipe로 포즈(33개 랜드마크)를 추출한다.
- "검출된 프레임 수" 뿐 아니라 "평가를 시도한 총 프레임 수(seen_frames)"도 반환해서
  검출률(detectionRate = detected/total)을 운영 지표로 노출한다.

왜 static_image_mode=False?
- 동영상엔 추적(tracking)이 들어가는 설정이 더 안정적인 결과를 준다(프레임 간 일관성↑).
"""

import cv2
import numpy as np
import mediapipe as mp
from typing import List, Dict, Tuple

mp_pose = mp.solutions.pose


class PoseExtractor:
    def __init__(self, step: int = 3):
        """
        step: 프레임 샘플링 간격(작을수록 정확, 클수록 빠름). 2~4 권장.
        """
        self.step = step
        # 동영상 모드 설정(추적 포함). 모델 복잡도 1은 속도/정확 밸런스용.
        self.pose = mp_pose.Pose(
            static_image_mode=False,
            model_complexity=1,
            enable_segmentation=False,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )

    def extract_from_video(
        self, video_path: str
    ) -> Tuple[np.ndarray, List[List[Dict[str, float]]], int]:
        """
        Returns:
          - landmarks_np: numpy array 버전(후처리 없으면 사용 안 해도 됨)
          - raw_data: List[frame][33] dict(x,y,z,visibility)
          - seen_frames: 샘플링 후 실제 평가 시도한 총 프레임 수 (검출률 계산용)
        """
        cap = cv2.VideoCapture(video_path)
        frame_idx = 0
        raw_data: List[List[Dict[str, float]]] = []
        seen_frames = 0

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            # step 단위로 프레임 다운샘플링(속도 개선)
            if frame_idx % self.step != 0:
                frame_idx += 1
                continue

            seen_frames += 1  # 이 프레임은 검출을 시도함

            # OpenCV는 BGR → MediaPipe는 RGB
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.pose.process(rgb)

            # 검출 성공한 프레임만 수집
            if results.pose_landmarks:
                keypoints = [
                    {"x": lm.x, "y": lm.y, "z": lm.z, "visibility": lm.visibility}
                    for lm in results.pose_landmarks.landmark
                ]
                raw_data.append(keypoints)

            frame_idx += 1

        cap.release()
        return np.array(raw_data), raw_data, seen_frames
