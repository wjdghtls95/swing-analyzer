"""
각도 계산 Domain Logic
포즈 데이터 → 각도 측정값 변환
"""
import numpy as np

from app.schemas.angle_dto import AngleCalculationResult, AngleMetrics
from app.schemas.pose_dto import PoseData, Keypoint


class AngleCalculator:
    """관절 각도 계산기"""

    def calculate(self, poses: list[PoseData]) -> AngleCalculationResult:
        """
        모든 프레임의 각도 계산

        Args:
            poses: 포즈 데이터 리스트

        Returns:
            AngleCalculationResult (프레임별 각도 + 평균)
        """
        angles_list = []

        for pose in poses:
            angles = AngleMetrics(
                frame_number=pose.frame_number,
                timestamp=pose.timestamp,
                left_elbow=self._calc_angle_3points(
                    pose.left_shoulder, pose.left_elbow, pose.left_wrist
                ),
                right_elbow=self._calc_angle_3points(
                    pose.right_shoulder, pose.right_elbow, pose.right_wrist
                ),
                left_knee=self._calc_angle_3points(
                    pose.left_hip, pose.left_knee, pose.left_ankle
                ),
                right_knee=self._calc_angle_3points(
                    pose.right_hip, pose.right_knee, pose.right_ankle
                ),
                left_hip=self._calc_angle_3points(
                    pose.left_shoulder, pose.left_hip, pose.left_knee
                ),
                right_hip=self._calc_angle_3points(
                    pose.right_shoulder, pose.right_hip, pose.right_knee
                ),
                x_factor=self._calc_x_factor(pose),
                shoulder_rotation=self._calc_shoulder_rotation(pose),
                hip_rotation=self._calc_hip_rotation(pose)
            )
            angles_list.append(angles)

        # 평균값 계산
        avg_left_elbow = np.mean([a.left_elbow for a in angles_list])
        avg_right_elbow = np.mean([a.right_elbow for a in angles_list])
        avg_left_knee = np.mean([a.left_knee for a in angles_list])
        avg_right_knee = np.mean([a.right_knee for a in angles_list])
        avg_x_factor = np.mean([a.x_factor for a in angles_list])

        return AngleCalculationResult(
            total_frames=len(poses),
            angles=angles_list,
            avg_left_elbow=avg_left_elbow,
            avg_right_elbow=avg_right_elbow,
            avg_left_knee=avg_left_knee,
            avg_right_knee=avg_right_knee,
            avg_x_factor=avg_x_factor
        )

    def _calc_angle_3points(self, p1: Keypoint, p2: Keypoint, p3: Keypoint) -> float:
        """3점으로 각도 계산 (p2가 꼭짓점)"""
        # 벡터 계산
        v1 = np.array([p1.x - p2.x, p1.y - p2.y])
        v2 = np.array([p3.x - p2.x, p3.y - p2.y])

        # 내적으로 각도 계산
        cos_angle = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2) + 1e-6)
        angle = np.arccos(np.clip(cos_angle, -1.0, 1.0))

        return np.degrees(angle)

    def _calc_x_factor(self, pose: PoseData) -> float:
        """X-Factor (어깨-엉덩이 회전 차이) 계산"""
        shoulder_rot = self._calc_shoulder_rotation(pose)
        hip_rot = self._calc_hip_rotation(pose)
        return abs(shoulder_rot - hip_rot)

    def _calc_shoulder_rotation(self, pose: PoseData) -> float:
        """어깨 회전 각도"""
        shoulder_vector = np.array([
            pose.right_shoulder.x - pose.left_shoulder.x,
            pose.right_shoulder.y - pose.left_shoulder.y
        ])
        return np.degrees(np.arctan2(shoulder_vector[1], shoulder_vector[0]))

    def _calc_hip_rotation(self, pose: PoseData) -> float:
        """엉덩이 회전 각도"""
        hip_vector = np.array([
            pose.right_hip.x - pose.left_hip.x,
            pose.right_hip.y - pose.left_hip.y
        ])
        return np.degrees(np.arctan2(hip_vector[1], hip_vector[0]))
