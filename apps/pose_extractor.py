import cv2
import mediapipe as mp

def extract_landmarks_from_video(video_path: str) -> list:
    mp_pose = mp.solutions.pose.Pose()
    cap = cv2.VideoCapture(video_path)
    landmarks = []
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret: break
        image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        result = mp_pose.process(image)
        if result.pose_landmarks:
            coords = [[lm.x, lm.y] for lm in result.pose_landmarks.landmark]
            landmarks.append(coords)
    cap.release()
    return landmarks