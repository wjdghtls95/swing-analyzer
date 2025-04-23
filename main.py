from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from analyze.router import router as analyze_router
from config.settings import settings

app = FastAPI(debug=settings.DEBUG)

@app.get("/")
def root():
    return {"message": "hello world"}

@app.get("/health", tags=["Health Check"])
def health_check():
    return {"status": "ok"}

app.include_router(analyze_router, prefix="/analyze")

app.openapi = lambda: get_openapi(
    title="AI Swing Analysis API",
    version="1.0.0",
    description="AI 골프 스윙 분석 API",
    routes=app.routes,
)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=True
    )


# import cv2
# import mediapipe as mp
#
# # Mediapipe pose 모듈 설정
# mp_pose = mp.solutions.pose
# pose = mp_pose.Pose()
# mp_drawing = mp.solutions.drawing_utils
#
# # 영상 불러오기
# # cap = cv2.VideoCapture(0)  # 실제 경로로 바꿔야 함
# cap = cv2.VideoCapture("data/swing.mp4")  # 실제 경로로 바꿔야 함
#
# while cap.isOpened():
#     ret, frame = cap.read()
#     if not ret:
#         break
#
#     # BGR을 RGB로 변환
#     image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
#
#     # Mediapipe로 포즈 추출
#     results = pose.process(image)
#
#     # 결과 시각화
#     if results.pose_landmarks:
#         mp_drawing.draw_landmarks(
#             frame,
#             results.pose_landmarks,
#             mp_pose.POSE_CONNECTIONS
#         )
#
#     # 화면에 출력
#     cv2.imshow('Golf Swing Analyzer', frame)
#
#     # q를 누르면 종료
#     if cv2.waitKey(10) & 0xFF == ord('q'):
#         break
#
# cap.release()
# cv2.destroyAllWindows()
#

# import os
# import cv2
# import mediapipe as mp
# import numpy as np
# import json
# from datetime import datetime
#
# # Mediapipe 설정
# mp_pose = mp.solutions.pose
# pose = mp_pose.Pose()
# mp_drawing = mp.solutions.drawing_utils
#
# os.makedirs("output", exist_ok=True)
#
# # 영상 불러오기
# cap = cv2.VideoCapture("data/swing.mp4")
#
# landmark_history = []  # 프레임별 관절 좌표 저장
#
# while cap.isOpened():
#     ret, frame = cap.read()
#     if not ret:
#         break
#
#     image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
#     results = pose.process(image)
#
#     if results.pose_landmarks:
#         # 33개 관절을 2D 좌표로 저장
#         frame_landmarks = []
#         for lm in results.pose_landmarks.landmark:
#             frame_landmarks.append([lm.x, lm.y])  # 0~1 정규화된 좌표
#         landmark_history.append(frame_landmarks)
#
#         # 화면에 시각화
#         mp_drawing.draw_landmarks(frame, results.pose_landmarks, mp_pose.POSE_CONNECTIONS)
#
#     cv2.imshow("Swing Analyzer", frame)
#     if cv2.waitKey(10) & 0xFF == ord('q'):
#         break
#
# cap.release()
# cv2.destroyAllWindows()
#
# # 분석 결과 저장 (임시 내용)
# result = {
#     "user_id": "jungho",
#     "swing_id": datetime.now().strftime("%Y%m%d_%H%M%S"),
#     "landmarks": landmark_history,
#     "analysis": {
#         "elbow": "pending",
#         "rotation": "pending"
#     },
#     "score": 0.0,
#     "label": "pending"
# }
#
# with open("output/results.json", "w") as f:
#     json.dump(result, f, indent=2)