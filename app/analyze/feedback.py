"""
왜 분리했나?
- '수치 → 한국어 코칭 문장'은 규칙/정책 레이어다.
- 수학(각도)과 분리하면 임계치 튜닝이나 A/B 테스트, JSON 외부화 등이 쉬워진다.
"""

def generate_feedback(angle: float, *, ideal: float = 135.0, tolerance: float = 15.0) -> str:
    """
    규칙 기반(룰 베이스) 피드백:
    - ideal±tolerance 내부면 '적절'
    - 낮으면 '과도한 굽힘'
    - 높으면 '과도한 폄'
    NaN(계산 실패)은 촬영 가이드 메시지로 유저 친화 처리.
    """
    if angle != angle:  # NaN 체크(자기 자신과 비교 시 NaN만 False)
        return "팔꿈치 각도를 계산할 수 없습니다. 조명이 밝고 팔이 잘 보이도록 촬영해 주세요."

    low, high = ideal - tolerance, ideal + tolerance
    if angle < low:
        return "팔꿈치가 과도하게 구부러졌습니다."
    if angle > high:
        return "팔꿈치가 너무 펴졌습니다."
    return "적절한 팔꿈치 각도입니다."