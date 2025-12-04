"""
포즈 추출 Domain Logic
MediaPipe Pose 사용
"""
import numpy as np
import mediapipe as mp

from app.schemas.pose_dto import PoseExtractionResult, PoseData, Keypoint


class PoseExtractor:
    """MediaPipe 기반 포즈 추출기"""

    def __init__(self, visibility_threshold: float = 0.5):
        self.visibility_threshold = visibility_threshold
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(
            static_image_mode=False,
            model_complexity=2,  # 0, 1, 2 (높을수록 정확하지만 느림)
            smooth_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )

    def extract(self, frames: list[np.ndarray], fps: float) -> PoseExtractionResult:
        """
        전체 프레임에서 포즈 추출

        Args:
            frames: RGB 이미지 리스트
            fps: 프레임 레이트

        Returns:
            PoseExtractionResult
        """
        poses = []

        for frame_idx, frame in enumerate(frames):
            timestamp = frame_idx / fps

            # MediaPipe 포즈 추정
            results = self.pose.process(frame)

            if results.pose_landmarks:
                # 33개 keypoints를 DTO로 변환
                landmarks = results.pose_landmarks.landmark

                # 주요 keypoint만 추출 (실제로는 33개 전부)
                pose_data = PoseData(
                    frame_number=frame_idx,
                    timestamp=timestamp,
                    nose=self._to_keypoint(landmarks[self.mp_pose.PoseLandmark.NOSE]),
                    left_shoulder=self._to_keypoint(landmarks[self.mp_pose.PoseLandmark.LEFT_SHOULDER]),
                    right_shoulder=self._to_keypoint(landmarks[self.mp_pose.PoseLandmark.RIGHT_SHOULDER]),
                    left_elbow=self._to_keypoint(landmarks[self.mp_pose.PoseLandmark.LEFT_ELBOW]),
                    right_elbow=self._to_keypoint(landmarks[self.mp_pose.PoseLandmark.RIGHT_ELBOW]),
                    left_wrist=self._to_keypoint(landmarks[self.mp_pose.PoseLandmark.LEFT_WRIST]),
                    right_wrist=self._to_keypoint(landmarks[self.mp_pose.PoseLandmark.RIGHT_WRIST]),
                    left_hip=self._to_keypoint(landmarks[self.mp_pose.PoseLandmark.LEFT_HIP]),
                    right_hip=self._to_keypoint(landmarks[self.mp_pose.PoseLandmark.RIGHT_HIP]),
                    left_knee=self._to_keypoint(landmarks[self.mp_pose.PoseLandmark.LEFT_KNEE]),
                    right_knee=self._to_keypoint(landmarks[self.mp_pose.PoseLandmark.RIGHT_KNEE]),
                    left_ankle=self._to_keypoint(landmarks[self.mp_pose.PoseLandmark.LEFT_ANKLE]),
                    right_ankle=self._to_keypoint(landmarks[self.mp_pose.PoseLandmark.RIGHT_ANKLE]),
                )

                # visibility 체크
                if self._is_valid_pose(pose_data):
                    poses.append(pose_data)

        self.pose.close()

        return PoseExtractionResult(
            total_frames=len(frames),
            poses=poses
        )

    def _to_keypoint(self, landmark) -> Keypoint:
        """MediaPipe Landmark → Keypoint DTO 변환"""
        return Keypoint(
            x=landmark.x,
            y=landmark.y,
            z=landmark.z,
            visibility=landmark.visibility
        )

    def _is_valid_pose(self, pose: PoseData) -> bool:
        """포즈가 유효한지 검증 (주요 keypoint visibility 체크)"""
        key_points = [
            pose.left_shoulder,
            pose.right_shoulder,
            pose.left_hip,
            pose.right_hip
        ]
        return all(kp.visibility >= self.visibility_threshold for kp in key_points)
