"""
페이즈 감지 Domain Logic
손목 Y좌표 변화로 6단계 스윙 페이즈 감지
"""
import numpy as np
from scipy.signal import savgol_filter, find_peaks

from app.schemas.angle_dto import AngleMetrics
from app.schemas.phase_dto import PhaseDetectionResult, PhaseInfo
from app.schemas.pose_dto import PoseData


class PhaseDetector:
    """스윙 6단계 페이즈 감지기"""

    def __init__(self, swing_direction: str = "right"):
        """
        Args:
            swing_direction: "right" (우타) 또는 "left" (좌타)
        """
        self.swing_direction = swing_direction

    def detect(
        self,
        poses: list[PoseData],
        angles: list[AngleMetrics],
        fps: float
    ) -> PhaseDetectionResult:
        """
        6단계 페이즈 감지

        Process:
        1. 손목 Y좌표 시계열 추출
        2. Savitzky-Golay 필터로 스무딩
        3. Peak/Valley 찾아 전환점 감지
        4. 6단계로 분류 (Address, Backswing, Top, Downswing, Impact, Follow-through)

        Args:
            poses: 포즈 데이터 리스트
            angles: 각도 데이터 리스트
            fps: 프레임 레이트

        Returns:
            PhaseDetectionResult (6개 페이즈 정보)
        """
        # 1. 주도 손목 선택 (우타: 왼손, 좌타: 오른손)
        wrist_y_coords = self._extract_wrist_y_coords(poses)

        # 2. Savitzky-Golay 필터 적용 (노이즈 제거)
        smoothed = self._smooth_signal(wrist_y_coords)

        # 3. 전환점 감지
        transition_frames = self._find_transition_points(smoothed)

        # 4. 6단계 페이즈 생성
        phases = self._create_phases(transition_frames, poses, angles, fps)

        return PhaseDetectionResult(phases=phases)

    def _extract_wrist_y_coords(self, poses: list[PoseData]) -> np.ndarray:
        """주도 손목의 Y좌표 시계열 추출"""
        if self.swing_direction == "right":
            # 우타자: 왼손목이 주도
            coords = [pose.left_wrist.y for pose in poses]
        else:
            # 좌타자: 오른손목이 주도
            coords = [pose.right_wrist.y for pose in poses]

        return np.array(coords)

    def _smooth_signal(self, signal: np.ndarray, window_length: int = 11, polyorder: int = 3) -> np.ndarray:
        """Savitzky-Golay 필터로 신호 스무딩"""
        if len(signal) < window_length:
            window_length = len(signal) if len(signal) % 2 == 1 else len(signal) - 1

        if window_length < polyorder + 2:
            polyorder = window_length - 2

        return savgol_filter(signal, window_length=window_length, polyorder=polyorder)

    def _find_transition_points(self, smoothed_signal: np.ndarray) -> dict[str, int]:
        """
        페이즈 전환점 프레임 찾기

        Returns:
            {
                "address_end": 10,      # Address → Backswing
                "top": 45,              # Backswing → Top (최고점)
                "downswing_start": 46,  # Top → Downswing
                "impact": 65,           # Downswing → Impact (최저점)
                "follow_start": 66      # Impact → Follow-through
            }
        """
        # Peak (최고점) 찾기 → Top
        peaks, _ = find_peaks(smoothed_signal, prominence=0.05)

        # Valley (최저점) 찾기 → Impact
        valleys, _ = find_peaks(-smoothed_signal, prominence=0.05)

        # 가장 큰 peak/valley 선택
        if len(peaks) == 0 or len(valleys) == 0:
            raise ValueError("Cannot detect swing phases - no clear peaks/valleys found")

        # Top: 가장 높은 peak
        top_frame = peaks[np.argmax(smoothed_signal[peaks])]

        # Impact: Top 이후 가장 낮은 valley
        valleys_after_top = valleys[valleys > top_frame]
        if len(valleys_after_top) == 0:
            # fallback: 전체에서 가장 낮은 valley
            impact_frame = valleys[np.argmin(smoothed_signal[valleys])]
        else:
            impact_frame = valleys_after_top[np.argmin(smoothed_signal[valleys_after_top])]

        # Address: 처음 5% 구간
        address_end = int(len(smoothed_signal) * 0.05)

        # Backswing start: Address 직후
        backswing_start = address_end + 1

        # Downswing start: Top 직후
        downswing_start = top_frame + 1

        # Follow-through start: Impact 직후
        follow_start = impact_frame + 1

        return {
            "address_end": address_end,
            "backswing_start": backswing_start,
            "top": top_frame,
            "downswing_start": downswing_start,
            "impact": impact_frame,
            "follow_start": follow_start,
            "video_end": len(smoothed_signal) - 1
        }

    def _create_phases(
        self,
        transitions: dict[str, int],
        poses: list[PoseData],
        angles: list[AngleMetrics],
        fps: float
    ) -> list[PhaseInfo]:
        """전환점 기반으로 6개 페이즈 생성"""

        # 각 페이즈 구간 정의
        phase_ranges = [
            ("Address", 0, transitions["address_end"]),
            ("Backswing", transitions["backswing_start"], transitions["top"]),
            ("Top", transitions["top"], transitions["downswing_start"]),
            ("Downswing", transitions["downswing_start"], transitions["impact"]),
            ("Impact", transitions["impact"], transitions["follow_start"]),
            ("Follow-through", transitions["follow_start"], transitions["video_end"])
        ]

        phases = []
        for phase_name, start_frame, end_frame in phase_ranges:
            # 시간 계산
            start_time = start_frame / fps
            end_time = end_frame / fps
            duration = end_time - start_time

            # 이 구간의 평균 각도 계산
            phase_angles = [a for a in angles if start_frame <= a.frame_number <= end_frame]
            representative_angles = self._calc_representative_angles(phase_angles)

            phase_info = PhaseInfo(
                name=phase_name,  # type: ignore (PhaseType은 Literal이라 자동 검증됨)
                start_frame=start_frame,
                end_frame=end_frame,
                start_time=start_time,
                end_time=end_time,
                duration=duration,
                representative_angles=representative_angles
            )
            phases.append(phase_info)

        return phases

    def _calc_representative_angles(self, phase_angles: list[AngleMetrics]) -> dict:
        """페이즈의 대표 각도 (평균) 계산"""
        if not phase_angles:
            return {}

        return {
            "left_elbow": float(np.mean([a.left_elbow for a in phase_angles])),
            "right_elbow": float(np.mean([a.right_elbow for a in phase_angles])),
            "left_knee": float(np.mean([a.left_knee for a in phase_angles])),
            "right_knee": float(np.mean([a.right_knee for a in phase_angles])),
            "x_factor": float(np.mean([a.x_factor for a in phase_angles])),
            "shoulder_rotation": float(np.mean([a.shoulder_rotation for a in phase_angles])),
            "hip_rotation": float(np.mean([a.hip_rotation for a in phase_angles]))
        }
