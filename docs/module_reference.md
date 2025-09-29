# Module Reference

본 문서는 내부 모듈/함수의 역할과 시그니처를 정리합니다.  
언더스코어(`_`) 프리픽스는 **모듈 외부로 노출되지 않는(의도상 private)** 헬퍼임을 의미합니다.

---

### 📦 app.analyze.service

**엔드투엔드 분석 파이프라인 + thresholds 룰 매칭 + 내부 로깅**

**Public API**

**analyze_swing(file_path, side=“right”, min_vis=0.5, norm_mode=NormMode.auto, club=None) -> dict**
- 전처리 → 포즈 추출 → 평균 메트릭 계산 → P2~P9 phase 지표 계산 → thresholds 룰 매칭 → 내부 로그 저장 → 결과 반환


- 반환: dict (metrics, phase_metrics, diagnosis_by_phase, swingId, preprocessMode, detectionRate 등)
  - 예시 코드:
  ```json
  {
  "swingId": "...",
  "metrics": {"elbow_avg": 133.8, "knee_avg": 130.8},
  "phase_metrics": {"P4": {"elbow": 108.4, "spine_tilt": 0.5}},
  "diagnosis_by_phase": {"P4": {"elbow_diag": "..."}, "AVG": {"knee_diag": "..."}}
		}
  ```


- 예외: HTTPException

**analyze_from_url(s3_url, side=“right”, min_vis=0.5, norm_mode=NormMode.auto) -> dict**
- 원격 URL(S3 등)을 다운로드 후 analyze_swing에 위임


- 주의: 임시 파일을 downloads/ 디렉토리에 저장 후 사용

---
### Private Helpers

**_do_preprocess(src_path: str, mode: NormMode) -> (str, str, int)**
- FFmpeg 기반 표준화 (코덱/해상도/FPS/미러 적용)


- 반환: (dst_path, used_mode, elapsed_ms)

**_load_thresholds() -> dict**
- thresholds.json 로드 후, ENV 존재 시 thresholds.{ENV}.json으로 덮어쓰기


- 모듈 import 시 1회 실행 → _THRESH 전역에 캐시

**_flatten_phase_rules(rules: dict) -> dict**
- rules["phases"] 내부 키("P4.elbow" 등)를 최상위로 평탄화


- **입출력 예시:**
  - **입력:** 
    ```json
    {"phases": {"P4.elbow": {...}}}
    ```

  - **출력:** 
      ```json
      {"P4.elbow": {...}}
      ```
 
**_select_rules_for_club(all_rules: dict, club) -> dict**
- default 규칙 위에 클럽별 규칙 얕은 덮어쓰기


- phases는 _flatten_phase_rules로 평탄화

**_apply_bins_metrics_dict(metrics: dict, rules: dict) -> dict**
- 메트릭 값에 thresholds bins(min/max) 룰 적용 → 진단 메시지 생성


- **입출력 예시:**
  - **입력:**
	```json	
	{"elbow_avg": 133.8, "P4.elbow": 108.4}
	```
  - 출력:	
    ```json
    {"elbow_diag": "…", "P4.elbow_diag": "…"}
    ```

**_group_diagnosis_by_phase(diagnosis: dict) -> dict**

- flat 진단 키를 phase별 dict로 재그룹화


- 지원 키 형태:
  - "P4.elbow_diag" (권장)
  - "P4_elbow_diag" (하위호환)
  -  "elbow_diag" → "AVG" 섹션에 배치
    - 입출력 예시:
      - 입력: 
      ```json
      {"elbow_diag": "...", "P4_elbow_diag": "...", "P7.knee_diag": "..."}
      ```
      - 출력: 
      ```json
      {
        "AVG": {"elbow_diag": "..."},
        "P4": {"elbow_diag": "..."},
        "P7": {"knee_diag": "..."}
      }
      ```

---

### 📦 app.analyze.angle

**팔꿈치·무릎·척추 각도 계산 (수학/기하 로직)**

**calculate_elbow_angle(landmarks, side=“right”, min_vis=0.5) -> float**
- 전체 시퀀스에서 팔꿈치 각도의 평균 계산

**calculate_knee_angle(landmarks, side=“right”, min_vis=0.5) -> float**
- 전체 시퀀스에서 무릎 각도의 평균 계산

**angles_at_frame(frame_landmarks, side=“right”) -> dict**
- 단일 프레임에서 elbow, knee, spine_tilt 계산


- 반환: 
	```json
	{"elbow": 130.9, "knee": 112.1, "spine_tilt": 6.0}
  ```

---

### 📦 app.analyze.phase

**스윙 phase(P2~P9) 인덱스 추정**

**detect_phases(landmarks) -> dict**
- 입력 프레임 길이 기반으로 P2~P9 인덱스 산출


- 반환: 
	```json
	{"P2": 0, "P3": 8, ... , "P9": 56} (부족 시 None)
	```

---

### 📦 app.analyze.extractor

**포즈 추출기 (MediaPipe 기반)**

PoseExtractor(step=3)
- 입력 영상에서 포즈 랜드마크 추출


- 메서드: extract_from_video(path) -> (landmarks_np, landmarks, total_seen)

--- 

### 📦 app.analyze.feedback

**generate_feedback(elbow_angle: float) -> Optional[str]**
- 평균 팔꿈치 각도를 기반으로 간단 요약 메시지 생성 (fallback 용)

--- 

### 📑 전체 Flow 요약
1. **전처리** → _do_preprocess
2. **포즈 추출** → PoseExtractor.extract_from_video
3. **평균 메트릭** → calculate_elbow_angle, calculate_knee_angle
4. **Phase 인덱스** → detect_phases
5. **Phase별 지표** → angles_at_frame
6. **룰 선택** → _select_rules_for_club
7. **룰 매칭** → _apply_bins_metrics_dict
8. **그룹화** → _group_diagnosis_by_phase
9. **로깅** → logs/ 디렉토리에 full_result 저장