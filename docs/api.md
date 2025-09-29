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
{
  "swingId": "cc17812d",
  "side": "right",
  "min_vis": 0.5,
  "club": "iron",
  "preprocessMode": "pro",
  "preprocessMs": 832,
  "detectedFrames": 67,
  "totalFrames": 67,
  "detectionRate": 1.0,
  "metrics": {
    "elbow_avg": 133.8,
    "knee_avg": 130.8
  },
  "phases": { "P2": 0, "P3": 8, "P4": 16, "P5": 24, "P6": 32, "P7": 40, "P8": 48, "P9": 56 },
  "phase_metrics": {
    "P4": { "elbow": 108.4, "knee": 77.1, "spine_tilt": 0.5 },
    "P7": { "elbow": 151.6, "knee": 149.7, "spine_tilt": 12.7 }
  },
  "diagnosis_by_phase": {
    "AVG": { "elbow_diag": "팔꿈치 각도가 적정 범위입니다(아이언 기준)." },
    "P4": {
      "elbow_diag": "백스윙 톱(P4)에서 팔꿈치가 과도하게 굽혀졌습니다.",
      "spine_tilt_diag": "P4에서 척추 기울기가 거의 없어 상체가 들렸습니다."
    },
    "P7": {
      "elbow_diag": "임팩트(P7) 팔꿈치 각도가 적정 범위입니다.",
      "knee_diag": "임팩트(P7) 무릎 각도가 적정 범위입니다."
    }
  }
}
```

---

## 참고
- Swagger UI: http://localhost:8080/docs  
- 전처리(FFmpeg) → 포즈 추출(MediaPipe) → 각도/메트릭 계산 → thresholds.json 기반 진단 생성