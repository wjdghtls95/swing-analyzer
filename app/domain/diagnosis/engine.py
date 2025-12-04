"""
진단 엔진 Domain Logic
Threshold 기반 룰 진단
"""
import json
from pathlib import Path

from app.schemas.diagnosis_dto import PhaseDiagnosis, DiagnosisResult
from app.schemas.phase_dto import PhaseInfo


class DiagnosisEngine:
    """Threshold 기반 스윙 진단 엔진"""

    def __init__(self, club: str = "driver"):
        """
        Args:
            club: 골프 클럽 종류 (driver, iron, wedge 등)
        """
        self.club = club
        self.thresholds = self._load_thresholds(club)

    def diagnose(self, phases: list[PhaseInfo]) -> DiagnosisResult:
        """
        전체 페이즈 진단

        Args:
            phases: 6개 페이즈 정보

        Returns:
            DiagnosisResult (페이즈별 진단 + 전체 점수)
        """
        diagnoses = []

        for phase in phases:
            diagnosis = self._diagnose_phase(phase)
            diagnoses.append(diagnosis)

        # 전체 점수 = 각 페이즈 점수 평균
        overall_score = sum(d.score for d in diagnoses) / len(diagnoses)

        return DiagnosisResult(
            diagnoses=diagnoses,
            overall_score=overall_score
        )

    def _diagnose_phase(self, phase: PhaseInfo) -> PhaseDiagnosis:
        """단일 페이즈 진단"""
        phase_name = phase.name
        angles = phase.representative_angles

        # 이 페이즈의 threshold 가져오기
        phase_thresholds = self.thresholds.get(phase_name, {})

        issues = []
        suggestions = []
        measured_values = {}
        deduction = 0  # 감점

        # 각도별 체크
        for metric_name, measured_value in angles.items():
            if metric_name not in phase_thresholds:
                continue

            threshold = phase_thresholds[metric_name]
            min_val = threshold.get("min")
            max_val = threshold.get("max")
            optimal = threshold.get("optimal")

            measured_values[metric_name] = {
                "measured": measured_value,
                "threshold_min": min_val,
                "threshold_max": max_val,
                "optimal": optimal
            }

            # 범위 체크
            if min_val is not None and measured_value < min_val:
                diff = min_val - measured_value
                issues.append(
                    f"{metric_name} 부족: {measured_value:.1f}도 (최소 {min_val:.1f}도 필요)"
                )
                suggestions.append(
                    f"{metric_name}을(를) {diff:.1f}도 증가시키세요"
                )
                deduction += 5

            elif max_val is not None and measured_value > max_val:
                diff = measured_value - max_val
                issues.append(
                    f"{metric_name} 과다: {measured_value:.1f}도 (최대 {max_val:.1f}도)"
                )
                suggestions.append(
                    f"{metric_name}을(를) {diff:.1f}도 감소시키세요"
                )
                deduction += 5

            # 최적값과 비교 (경고만)
            elif optimal is not None:
                diff = abs(measured_value - optimal)
                if diff > 10:  # 10도 이상 차이
                    suggestions.append(
                        f"{metric_name} 최적화 가능: 현재 {measured_value:.1f}도, 최적 {optimal:.1f}도"
                    )
                    deduction += 2

        # 점수 계산 (100점 만점에서 감점)
        score = max(0, 100 - deduction)

        return PhaseDiagnosis(
            phase=phase_name,
            score=score,
            issues=issues,
            suggestions=suggestions,
            measured_values=measured_values
        )

    def _load_thresholds(self, club: str) -> dict:
        """
        클럽별 threshold 로드

        Expected structure:
        {
            "Backswing": {
                "left_elbow": {"min": 160, "max": 170, "optimal": 165},
                "x_factor": {"min": 40, "max": 60, "optimal": 50}
            },
            "Downswing": { ... }
        }
        """
        # threshold 파일 경로 (기존 코드의 경로 사용)
        threshold_file = Path(__file__).parent.parent.parent / "config" / "thresholds" / f"{club}.json"

        if not threshold_file.exists():
            # fallback: driver 기본값
            threshold_file = Path(__file__).parent.parent.parent / "config" / "thresholds" / "driver.json"

        if not threshold_file.exists():
            # 하드코딩된 기본값 (실제로는 파일에서 로드)
            return self._get_default_thresholds()

        with open(threshold_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def _get_default_thresholds(self) -> dict:
        """기본 threshold (파일 없을 때)"""
        return {
            "Address": {
                "left_elbow": {"min": 140, "max": 160, "optimal": 150},
                "right_knee": {"min": 160, "max": 180, "optimal": 170}
            },
            "Backswing": {
                "left_elbow": {"min": 160, "max": 180, "optimal": 170},
                "x_factor": {"min": 40, "max": 60, "optimal": 50}
            },
            "Top": {
                "left_elbow": {"min": 150, "max": 170, "optimal": 160},
                "shoulder_rotation": {"min": 80, "max": 100, "optimal": 90}
            },
            "Downswing": {
                "left_elbow": {"min": 140, "max": 160, "optimal": 150},
                "x_factor": {"min": 30, "max": 50, "optimal": 40}
            },
            "Impact": {
                "left_elbow": {"min": 160, "max": 180, "optimal": 170},
                "left_knee": {"min": 160, "max": 180, "optimal": 170}
            },
            "Follow-through": {
                "left_elbow": {"min": 150, "max": 170, "optimal": 160}
            }
        }
