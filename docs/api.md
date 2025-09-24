# API 명세

## 1) 업로드 파일 분석
- **Endpoint**: `POST /analyze`
- **Form fields**
  - `file`: MP4 파일 (required)
  - `side`: `"right"` | `"left"` (default: `"right"`)
  - `min_vis`: float, 0.0 ~ 1.0 (default: `0.5`)
  - `norm_mode`: `"auto" | "basic" | "pro"` (default: `auto`)

### 예시 (curl)
```bash
curl -X POST "http://localhost:8080/analyze" \
  -F "file=@samples/driver.mp4" \
  -F "side=right" \
  -F "min_vis=0.5" \
  -F "norm_mode=auto"
```

### Response 예시 
```json
{
  "swingId": "f3c0e0fc",
  "side": "right",
  "min_vis": 0.5,
  "preprocessMode": "pro",
  "preprocessMs": 681,
  "detectedFrames": 80,
  "totalFrames": 80,
  "detectionRate": 1.0,
  "metrics": {
    "elbow_avg": 110.9,
    "knee_avg": 128.4
  },
  "diagnosis": {
    "elbowDiag": "팔꿈치 굴곡이 큰 편입니다.",
    "kneeDiag": "무릎 굴곡이 큰 편입니다."
  }
}
```

--

## 참고
- Swagger UI: http://localhost:8080/docs  
- 전처리(FFmpeg) → 포즈 추출(MediaPipe) → 각도/메트릭 계산 → thresholds.json 기반 진단 생성