# Thresholds 가이드

## 개요
app/config/thresholds.json 은 지표별(예: elbow_avg, knee_avg)로  
진단 메시지를 규칙 기반(bins)으로 정의하는 설정 파일입니다.

## 구조
매칭 규칙: (min ≤ 값 < max)  
min 또는 max가 없으면 각각 -∞, +∞로 간주

### 예시
```json
{
  "elbow_avg": {
    "bins": [
      { "max": 100, "msg": "팔꿈치가 과도하게 구부러졌습니다." },
      { "min": 100, "max": 120, "msg": "팔꿈치 굴곡이 큰 편입니다." },
      { "min": 120, "max": 150, "msg": "팔꿈치 각도가 적정 범위입니다." },
      { "min": 150, "msg": "팔꿈치가 다소 펴지는 경향이 있습니다." }
    ]
  },
  "knee_avg": {
    "bins": [
      { "max": 120, "msg": "무릎 굴곡이 매우 큽니다." },
      { "min": 120, "max": 140, "msg": "무릎 굴곡이 큰 편입니다." },
      { "min": 140, "max": 165, "msg": "무릎 각도가 적정 범위입니다." },
      { "min": 165, "msg": "무릎이 펴지는 경향이 있습니다." }
    ]
  }
}
```

## 운영 팁
- 지표 키는 코드의 metrics 키와 동일해야 함 (elbow_avg, knee_avg 등)
- 문구만 수정해도 즉시 진단 결과가 바뀜 (배포 없이 운영 튜닝 가능)

## ENV 오버라이드
- thresholds.{ENV}.json 으로 일부 키만 덮어쓰기 가능 (예: thresholds.prod.json)
- 현재 로더는 기본 파일 → ENV 파일 순서로 병합 적용