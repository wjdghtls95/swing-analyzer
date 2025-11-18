# 🏌️ Golf Swing Analyzer

**AI 기반 골프 스윙 자동 분석 시스템**

Mediapipe와 OpenCV를 활용한 골프 스윙 동작 분석 및 진단 API입니다. 실시간으로 스윙 영상을 분석하여 자세 평가, 각도 측정, 개선점을 제공합니다.

---

## ✨ 주요 기능

- **🎯 자세 추정**: Mediapipe 기반 33개 관절 포인트 실시간 추적
- **📊 스윙 단계 분석**: Address → Backswing → Top → Downswing → Impact → Follow-through 자동 구분
- **🔍 각도 측정**: 팔꿈치, 무릎, 척추 각도 실시간 계산
- **💡 AI 진단**: Keras 기반 LSTM 모델로 스윙 패턴 분석 및 개선점 제안
- **🚀 REST API**: FastAPI 기반 고성능 비동기 처리
- **☁️ 클라우드 연동**: AWS S3 자동 업로드 및 결과 저장

---

## 🛠️ 기술 스택

### Backend & API
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat&logo=fastapi&logoColor=white)
![Uvicorn](https://img.shields.io/badge/Uvicorn-499848?style=flat&logo=gunicorn&logoColor=white)

### AI & Machine Learning
![Keras](https://img.shields.io/badge/Keras-D00000?style=flat&logo=keras&logoColor=white)
![TensorFlow](https://img.shields.io/badge/TensorFlow-FF6F00?style=flat&logo=tensorflow&logoColor=white)
![Mediapipe](https://img.shields.io/badge/Mediapipe-0097A7?style=flat&logo=google&logoColor=white)

### Computer Vision

![OpenCV](https://img.shields.io/badge/OpenCV-5C3EE8?style=flat&logo=opencv&logoColor=white)
![FFmpeg](https://img.shields.io/badge/FFmpeg-007808?style=flat&logo=ffmpeg&logoColor=white)

### Data Processing

![NumPy](https://img.shields.io/badge/NumPy-013243?style=flat&logo=numpy&logoColor=white)
![Pandas](https://img.shields.io/badge/Pandas-150458?style=flat&logo=pandas&logoColor=white)
![Matplotlib](https://img.shields.io/badge/Matplotlib-11557c?style=flat&logo=python&logoColor=white)
![Jupyter](https://img.shields.io/badge/Jupyter-F37626?style=flat&logo=jupyter&logoColor=white)

### Infrastructure

![AWS S3](https://img.shields.io/badge/AWS_S3-569A31?style=flat&logo=amazons3&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?style=flat&logo=docker&logoColor=white)
---

## 🚀 빠른 시작

### Docker로 실행 (권장)

```bash
docker-compose up -d
```

### 로컬 환경 실행

```bash
# 1. 레포지토리 클론
git clone https://github.com/wjdghtls95/swing-analyzer.git
cd swing-analyzer

# 2. 가상환경 생성 및 활성화
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. 의존성 설치
pip install -r requirements.txt

# 4. 서버 실행
python app/main.py

```

### API 테스트

```bash
curl -X POST "http://localhost:8000/analyze" \
  -F "video=@sample_swing.mp4"
```

---

## 📈 분석 결과 예시

```json
{
  "swing_phases": [
    {"phase": "address", "frame": 0, "timestamp": 0.0},
    {"phase": "backswing", "frame": 15, "timestamp": 0.5},
    {"phase": "impact", "frame": 45, "timestamp": 1.5}
  ],
  "angles": {
    "left_elbow": [160, 145, 130, 95, 170],
    "right_knee": [175, 170, 165, 155, 180]
  },
  "diagnosis": {
    "score": 78,
    "issues": ["백스윙 시 왼팔 각도 부족", "임팩트 타이밍 0.1초 빠름"],
    "suggestions": ["팔꿈치 각도를 90도까지 구부리세요", "하체 회전을 먼저 시작하세요"]
  }
}

```

---

## 📁 프로젝트 구조

```
swing-analyzer/
├── app/
│   ├── analyze/        # 스윙 분석 로직
│   ├── api/           # FastAPI 라우터
│   ├── config/        # 설정 파일
│   ├── llm/           # LLM 통합 (진단 메시지 생성)
│   ├── ml/            # 머신러닝 모델 (LSTM)
│   ├── report/        # 리포트 생성
│   ├── storage/       # S3 업로드
│   └── main.py        # 진입점
├── docs/              # 문서
│   ├── api.md         # API 명세
│   ├── dev_guide.md   # 개발 가이드
│   ├── module_reference.md  # 모듈 레퍼런스
│   └── thresholds.md  # 임계값 설정
├── notebooks/         # Jupyter 노트북 (EDA, 모델 실험)
├── tests/            # 단위 테스트
└── docker-compose.yml

```

---

## 📚 문서

- [**API 명세**](https://www.genspark.ai/docs/api.md) - 엔드포인트 및 요청/응답 스키마
- [**개발 가이드**](https://www.genspark.ai/docs/dev_guide.md) - 로컬 개발 환경 설정
- [**모듈 레퍼런스**](https://www.genspark.ai/docs/module_reference.md) - 각 모듈의 함수 및 클래스
- [**임계값 설정**](https://www.genspark.ai/docs/thresholds.md) - 각도 임계값 및 Phase Detection 파라미터

---

## 🔬 주요 기능 상세

### 1. Pose Estimation

- Mediapipe Pose로 33개 랜드마크 실시간 추적
- 2D 좌표 + Visibility 점수로 가려진 부위 처리
- 60 FPS 영상 처리 속도 (CPU 기준)

### 2. Phase Detection

- 손목 Y축 좌표 변화율 기반 단계 구분
- Savitzky-Golay 필터로 노이즈 제거
- 6단계 자동 분류 (Address, Backswing, Top, Downswing, Impact, Follow-through)

### 3. Diagnosis Engine

- LSTM 모델로 시계열 각도 데이터 학습
- 프로 골퍼 데이터셋과 비교하여 점수 산출
- LLM 기반 자연어 피드백 생성

---

## 🧪 테스트

```bash
# 전체 테스트 실행
pytest

# 커버리지 확인
pytest --cov=app tests/

```
---