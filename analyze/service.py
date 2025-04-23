from analyze.extractor import extract_pose
from analyze.angle import calculate_elbow_angle
from analyze.feedback import generate_feedback
import requests, os, shutil, uuid

def analyze_swing(file_path: str) -> dict:
    landmarks = extract_pose(file_path)
    elbow_angle = calculate_elbow_angle(landmarks)
    feedback = generate_feedback(elbow_angle)
    return {
        "swingId": file_path.split("/")[-1].split("_")[0],
        "elbowAvgAngle": elbow_angle,
        "feedback": feedback,
        "landmarkCount": len(landmarks)
    }

def analyze_from_url(s3_url: str) -> dict:
    os.makedirs("downloads", exist_ok=True)
    filename = f"downloads/{uuid.uuid4().hex[:8]}.mp4"
    response = requests.get(s3_url, stream=True)
    with open(filename, "wb") as f:
        shutil.copyfileobj(response.raw, f)
    return analyze_swing(filename)


# def analyze_swing(video_path: str):
#     all_landmarks = extract_landmarks_from_video(video_path)
#     elbow_angles = []
#
#     for lm in all_landmarks:
#         shoulder = lm[12]
#         elbow = lm[14]
#         wrist = lm[16]
#         angle = calculate_angle(shoulder, elbow, wrist)
#         elbow_angles.append(angle)
#
#     avg_angle = sum(elbow_angles) / len(elbow_angles)
#     feedback = elbow_feedback(avg_angle)
#
#     result = {
#         "user_id": "tester",
#         "swing_id": datetime.now().strftime("%Y%m%d_%H%M%S"),
#         "elbow_avg_angle": round(avg_angle, 2),
#         "feedback": feedback,
#         "landmark_count": len(all_landmarks)
#     }
#
#     with open("output/results.json", "w") as f:
#         json.dump(result, f, indent=2)
#
#     return result