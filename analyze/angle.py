import numpy as np

# def calculate_angle(a, b, c):
#     a = np.array(a)
#     b = np.array(b)
#     c = np.array(c)
#     ba = a - b
#     bc = c - b
#     cosine = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc))
#     angle = np.arccos(np.clip(cosine, -1.0, 1.0))
#     return np.degrees(angle)

def calculate_elbow_angle(landmarks) -> float:
    # TODO: 어깨-팔꿈치-손목 각도 계산
    return 147.6