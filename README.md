# 🏌️‍♂️ Golf Swing Analyzer (with Mediapipe + OpenCV)

> 골프 스윙 동작을 영상으로 분석하고, 팔꿈치 각도 등 스윙 폼의 문제를 추적하는 Python 기반 프로젝트

---

## 📦 사용 기술

- Python 3.9
- [OpenCV](https://opencv.org/)
- [Mediapipe (Pose)](https://google.github.io/mediapipe/)
- Numpy

---

## ⚙️ 기능 요약

- Mediapipe를 통한 실시간 관절 추적
- 팔꿈치 각도 실시간 측정 및 평가 메시지 출력
- 기본 영상 기반 분석 루프 구성
- (예정) 백스윙/다운스윙 분리, 클럽 경로 추적, AI 모델 평가

---

## 🖥 실행 방법

```bash
git clone https://github.com/your-username/golf-swing-analyzer.git
cd golf-swing-analyzer

# 가상환경 생성 후 활성화
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
# 또는
.venv\Scripts\activate  # Windows

# 패키지 설치
pip install -r requirements.txt

# 영상 파일 준비
# data/swing.mp4 위치에 스윙 영상 넣기

# 실행
python main.py