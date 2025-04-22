from apps.pose_extractor import extract_landmarks_from_video
from apps.angle import calculate_angle
from apps.feedback import elbow_feedback
from datetime import datetime
import json


def analyze_swing(video_path: str):
    all_landmarks = extract_landmarks_from_video(video_path)
    elbow_angles = []

    for lm in all_landmarks:
        shoulder = lm[12]
        elbow = lm[14]
        wrist = lm[16]
        angle = calculate_angle(shoulder, elbow, wrist)
        elbow_angles.append(angle)

    avg_angle = sum(elbow_angles) / len(elbow_angles)
    feedback = elbow_feedback(avg_angle)

    result = {
        "user_id": "tester",
        "swing_id": datetime.now().strftime("%Y%m%d_%H%M%S"),
        "elbow_avg_angle": round(avg_angle, 2),
        "feedback": feedback,
        "landmark_count": len(all_landmarks)
    }

    with open("output/results.json", "w") as f:
        json.dump(result, f, indent=2)

    return result