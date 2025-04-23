# import json
#
# def load_elbow_reference():
#     with open("config/elbow_reference.json") as f:
#         return json.load(f)
#
# def elbow_feedback(angle: float):
#     ref = load_elbow_reference()
#     ideal = ref["ideal"]
#     tol = ref["tolerance"]
#
#     if abs(angle - ideal) <= tol:
#         return "팔꿈치 각도가 적절합니다."
#     elif angle < ideal - tol:
#         return "팔꿈치가 너무 굽혀졌습니다."
#     else:
#         return "팔꿈치가 너무 펴졌습니다."

def generate_feedback(angle: float) -> str:
    if angle > 150:
        return "팔꿈치가 너무 펴졌습니다."
    elif angle < 100:
        return "팔꿈치가 과도하게 구부러졌습니다."
    return "적절한 팔꿈치 각도입니다."
