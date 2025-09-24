# 개발 환경 가이드

## 요구사항
- Python 3.9+
- FFmpeg 설치 (macOS)
  brew install ffmpeg

## 가상환경 & 설치
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

## 환경변수 (.env 예시)
프로젝트 루트에 .env 파일 생성:
ENV=local
FASTAPI_PORT=8080
DEBUG_MODE=true

VIDEO_FPS=30
VIDEO_HEIGHT=720
VIDEO_MIRROR=false
POSE_FRAME_STEP=3

## Thresholds 파일
cp app/config/thresholds.base.json app/config/thresholds.json

## 서버 실행

### (A) CLI로 실행
uvicorn app.main:app --reload --port 8080
# 또는
python -m app.main

### (B) PyCharm 디버깅
- reload=True 는 서브프로세스를 띄워 브레이크포인트가 안 걸릴 수 있음  
- 디버깅 시에는 reload=False로 단일 프로세스로 실행 권장

옵션 1: main.py 직접 실행
1. Run/Debug Configurations → + Python
2. Script path: app/main.py
3. Working directory: 프로젝트 루트
4. Parameters: 없음
5. Environment: .env 필요시 지정
6. uvicorn.run(..., reload=False)

옵션 2: 모듈 실행으로 uvicorn 호출
1. Run/Debug Configurations → + Python
2. Module name: uvicorn
3. Parameters: app.main:app --port 8080
4. Working directory: 프로젝트 루트

## 프로젝트 구조
```
swing-analyzer/
  app/
    api/
    analyze/
    config/
      thresholds.base.json
      thresholds.json
    main.py
  docs/
    README.md
    api.md
    thresholds.md
    dev_guide.md
  logs/
  downloads/
  normalized/
  .env
  requirements.txt
```
