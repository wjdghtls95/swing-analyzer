# API 명세

## 1) 업로드 파일 분석
- **Endpoint**: `POST /analyze`
- **Form fields**
  - `file`: MP4 파일 (required)
  - `side`: `"right"` | `"left"` (default: `"right"`)
  - `min_vis`: float, 0.0 ~ 1.0 (default: `0.5`)
  - `norm_mode`: `"auto" | "basic" | "pro"` (default: `auto`)
  - `club: "driver"|"iron"|"wedge"|"putter" (optional)`

### 예시 (curl)
```bash
curl -X POST "http://localhost:your_port/analyze" \
  -F "file=@samples/iron.mp4" \
  -F "side=right" \
  -F "min_vis=0.5" \
  -F "norm_mode=auto" \
  -F "club=iron"
```

### Response 예시 
```json
// ------ Response Body ------ 
{
  "swingId": "19721cda",
  "input": {
    "filePath": "uploads/19721cda_골프 스윙.mp4",
    "side": "right",
    "club": "iron"
  },
  "env": "test",
  "appVersion": "unknown",
  "timestamp": 1760899118,
  "preprocess": {
    "mode": "pro",
    "ms": 7022,
    "fps": 30,
    "height": 720,
    "mirror": false
  },
  "pose": {
    "frameStep": 3,
    "minVisibility": 0.5
  },
  "phase": {
    "method": "ml"
  },
  "detectedFrames": 80,
  "totalFrames": 80,
  "detectionRate": 1,
  "metrics": {
    "elbow_avg": 110.9,
    "knee_avg": 128.4
  },
  "phases": {
    "P2": 0,
    "P3": 62,
    "P5": 76,
    "P6": 77,
    "P7": 19,
    "P8": 2,
    "P9": 41
  },
  "phase_metrics": {
    "P2": {
      "elbow": 100.6,
      "knee": 60.7,
      "spine_tilt": 1.4,
      "shoulder_turn": -178.2,
      "hip_turn": 178.7,
      "x_factor": 3.1
    },
    "P3": {
      "elbow": 113.3,
      "knee": 152,
      "spine_tilt": 21.8,
      "shoulder_turn": 5.8,
      "hip_turn": -172.7,
      "x_factor": 60
    },
    "P5": {
      "elbow": 8.7,
      "knee": 145.9,
      "spine_tilt": 15.8,
      "shoulder_turn": 8.7,
      "hip_turn": -173.3,
      "x_factor": -60
    },
    "P6": {
      "elbow": 28.9,
      "knee": 138.5,
      "spine_tilt": 15.9,
      "shoulder_turn": 11.6,
      "hip_turn": -173.3,
      "x_factor": -60
    },
    "P7": {
      "elbow": 85.6,
      "knee": 32.1,
      "spine_tilt": 2.4,
      "shoulder_turn": 179.8,
      "hip_turn": 178.7,
      "x_factor": 1
    },
    "P8": {
      "elbow": 93.3,
      "knee": 136.2,
      "spine_tilt": 3,
      "shoulder_turn": -178.1,
      "hip_turn": 177.8,
      "x_factor": 4.1
    },
    "P9": {
      "elbow": 172.5,
      "knee": 144.1,
      "spine_tilt": 3.4,
      "shoulder_turn": 179.9,
      "hip_turn": 177.8,
      "x_factor": 2.1
    }
  }
}
```

---

## 참고
- Swagger UI: `http://localhost:your_port/docs`  
- 전처리(FFmpeg) → 포즈 추출(MediaPipe) → 각도/메트릭 계산 → thresholds.json 기반 진단 생성