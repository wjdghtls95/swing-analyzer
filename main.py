import cv2
import mediapipe as mp

# Mediapipe pose 모듈 설정
mp_pose = mp.solutions.pose
pose = mp_pose.Pose()
mp_drawing = mp.solutions.drawing_utils

# 영상 불러오기
# cap = cv2.VideoCapture(0)  # 실제 경로로 바꿔야 함
cap = cv2.VideoCapture("data/swing.mp4")  # 실제 경로로 바꿔야 함

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    # BGR을 RGB로 변환
    image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    # Mediapipe로 포즈 추출
    results = pose.process(image)

    # 결과 시각화
    if results.pose_landmarks:
        mp_drawing.draw_landmarks(
            frame,
            results.pose_landmarks,
            mp_pose.POSE_CONNECTIONS
        )

    # 화면에 출력
    cv2.imshow('Golf Swing Analyzer', frame)

    # q를 누르면 종료
    if cv2.waitKey(10) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()