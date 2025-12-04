"""
진단 결과 관련 DTO
DiagnosisEngine 입출력용
"""
from pydantic import BaseModel, Field

class PhaseDiagnosis(BaseModel):
    """1개 페이즈의 진단 결과"""
    phase: str
    score: float = Field(..., ge=0.0, le=100.0)

    # 룰 기반 진단 결과
    issues: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)

    # 세부 측정값 (디버깅용)
    measured_values: dict = Field(
        default_factory=dict,
        example={"left_elbow": 145.2, "threshold_min": 160, "threshold_max": 170}
    )


class DiagnosisResult(BaseModel):
    """전체 진단 결과"""
    diagnoses: list[PhaseDiagnosis] = Field(..., min_items=6, max_items=6)
    overall_score: float = Field(..., ge=0.0, le=100.0)

    def get_diagnosis_for_phase(self, phase_name: str) -> PhaseDiagnosis:
        """특정 페이즈 진단 반환"""
        for diagnosis in self.diagnoses:
            if diagnosis.phase == phase_name:
                return diagnosis
        raise ValueError(f"Diagnosis for phase {phase_name} not found")
