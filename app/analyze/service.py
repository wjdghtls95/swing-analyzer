"""
왜 이렇게 조립했나?
- B안: 클라이언트에는 '요약'만 돌려주되, 내부에는 '풀데이터'를 파일로 로깅.
- thresholds.json 룰을 적용해 diagnosis(다항목)를 만들고, logs에 함께 저장 → ML/튜닝 준비.
- 향후 /analyze/full 엔드포인트를 열면 같은 풀데이터를 즉시 노출 가능(확장성).
"""
import os, shutil, uuid, time, json, requests, logging
from pathlib import Path
from fastapi import HTTPException

from app.analyze.constants import DIAG_KEY_MAP, ALIAS
from app.analyze.extractor import PoseExtractor
from app.analyze.angle import calculate_elbow_angle, calculate_knee_angle  # ← 무릎 함수 사용
from app.analyze.feedback import generate_feedback
from app.analyze.schema import NormMode
from app.config.settings import settings
from app.analyze.preprocess import normalize_video, normalize_video_pro

# ---------- 로거 ----------
logger = logging.getLogger(__name__)
if not logging.getLogger().handlers:
    # 글로벌 로거가 설정 안되어 있으면 기본 설정 (운영에서 uvicorn 로거가 대체)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

# ---------- 내부 로깅 디렉토리 ----------
_LOG_DIR = os.path.join("logs")
os.makedirs(_LOG_DIR, exist_ok=True)

# ---------- thresholds 로더 ----------
def _load_thresholds() -> dict:
    """
    왜 분리했나?
    - 코드와 임계치/문구 정책을 분리해서 배포 없이 운영 튜닝을 가능하게 하려는 목적.
    - ENV별 파일 지원(예: thresholds.prod.json) → 없으면 기본 thresholds.json 사용.

    기본 thresholds.json을 먼저 읽고,
    ENV가 있으면 thresholds.{ENV}.json으로 '덮어쓴다'(merge 느낌).
    → ENV 파일이 일부 키만 있어도 나머지는 기본에서 가져옴.
    """
    here = Path(__file__).resolve()
    # service.py -> analyze -> app
    app_root = here.parents[2]
    config_dir = app_root / "app" / "config"

    env = getattr(settings, "ENV", None)
    merged = {}
    tried = []

    # 1) base
    base = config_dir / "thresholds.json"
    tried.append(str(base))
    if base.exists():
        try:
            with base.open("r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                merged.update(data)
        except Exception as e:
            logger.warning(f"[THRESH] failed to load base {base}: {e}")

    # 2) env override
    if env:
        envf = config_dir / f"thresholds.{env}.json"
        tried.append(str(envf))
        if envf.exists():
            try:
                with envf.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    merged.update(data)
            except Exception as e:
                logger.warning(f"[THRESH] failed to load env {envf}: {e}")

    logger.info(f"[THRESH] searched={tried} loaded keys={list(merged.keys())}")

    return merged


_THRESH = _load_thresholds()
if not _THRESH:
    logger.warning("[THRESH] WARNING: no thresholds loaded. diagnosis may be empty.")

def _apply_bins_metrics_dict(metrics: dict) -> dict:
    """
    metrics에 실제로 존재하는 지표들을 기준으로 진단을 생성한다.
    - 우선순위: thresholds 파일(_THRESH)에 해당 지표 룰이 있으면 그걸 사용
    - 없으면(ENV/경로 이슈 등) 그 지표는 스킵(= elbow는 fallback로 커버되고,
      knee가 스킵되던 문제가 있었음) → 이를 방지하려면 default를 쓰면 되지만,
      지금 요청은 '추가 말고 수정'이므로 여기서는 파일 룰만 사용.
    - 매칭 정책: (min 없으면 -inf) ≤ val < (max 없으면 +inf)
    """
    out = {}
    for metric_name, val in metrics.items():
        if val is None or val != val:  # None/NaN
            continue

        # 1) 정확 키 -> alias 순으로 룰 찾기
        spec = _THRESH.get(metric_name)
        # 2) alias
        if not spec:
            for alias in ALIAS.get(metric_name, []):
                spec = _THRESH.get(alias)
                if spec:
                    break
        if not spec:
            # 디버깅 도움 로그(원치 않으면 지워도 됨)
            logger.debug(f"[THRESH] no rule for '{metric_name}' (available keys={list(_THRESH.keys())})")
            continue

        for b in spec.get("bins", []):
            mn = b.get("min", float("-inf"))
            mx = b.get("max", float("inf"))
            if mn <= val < mx:
                msg = b.get("msg")
                if msg:
                    key = DIAG_KEY_MAP.get(metric_name, metric_name)
                    out[key] = msg
                break

    return out

# ---------- 전처리 ----------
def _do_preprocess(src_path: str, mode: NormMode):
    """
    입력 영상 표준화 단계:
    - basic: 항상 재인코딩(안정) / pro: 하드웨어 인코딩 or smart_copy(속도↑)
    - auto: pro 시도 후 실패 시 basic fallback
    반환: (표준화 경로, 사용 모드 문자열, 처리 시간(ms))
    """
    dst_dir = os.path.join("normalized")
    os.makedirs(dst_dir, exist_ok=True)
    dst_path = os.path.join(dst_dir, f"{uuid.uuid4().hex[:8]}.mp4")

    t0 = time.perf_counter()
    used_mode = None

    fps = settings.VIDEO_FPS
    height = settings.VIDEO_HEIGHT
    mirror = settings.VIDEO_MIRROR

    try:
        if mode == NormMode.basic:
            normalize_video(src_path, dst_path, fps=fps, height=height, mirror=mirror)
            used_mode = "basic"
        elif mode == NormMode.pro:
            normalize_video_pro(src_path, dst_path, fps=fps, height=height, mirror=mirror)
            used_mode = "pro"
        else:  # auto
            try:
                normalize_video_pro(src_path, dst_path, fps=fps, height=height, mirror=mirror)
                used_mode = "pro"
            except Exception:
                normalize_video(src_path, dst_path, fps=fps, height=height, mirror=mirror)
                used_mode = "basic"
    except FileNotFoundError as e:
        raise HTTPException(status_code=422, detail=f"input not found: {e}") from e
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=f"preprocess failed: {e}") from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"unexpected preprocess error: {e}") from e
    finally:
        ms = int((time.perf_counter() - t0) * 1000)

    return dst_path, used_mode, ms

# ---------- 메인 파이프라인 ----------
def analyze_swing(file_path: str, side: str = "right", min_vis: float = 0.5,
                  norm_mode: NormMode = NormMode.auto) -> dict:

    """
    엔드투엔드 분석 파이프라인(B안):
      1) 전처리(코덱/해상도/FPS 표준화)
      2) 포즈 추출(샘플링/추적)
      3) 핵심 메트릭 계산(elbow_avg, knee_avg)
      4) 단일 요약 메시지(feedback) + 다항목 진단(diagnosis; 내부 로깅용)
      5) 검출률/메타 계산
      6) 내부 로깅(full_result) 저장 → 최종 응답은 요약만 반환
    """
    # 1) 전처리
    try:
        norm_path, used_mode, preprocess_ms = _do_preprocess(file_path, norm_mode)
    except FileNotFoundError as e:
        raise HTTPException(status_code=422, detail=f"Input not found: {e}")
    except RuntimeError as e:
        # ffmpeg/ffprobe not found 등 커맨드 실패
        raise HTTPException(status_code=500, detail=f"Preprocess failed: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")

    # 2) 포즈 추출
    extractor = PoseExtractor(step=getattr(settings, "POSE_FRAME_STEP", 3))
    landmarks_np, landmarks, total_seen = extractor.extract_from_video(norm_path)

    # 3) 메트릭 계산 (평균값 이후 P4/P7 등 구간값 확장 가능)
    elbow_angle = calculate_elbow_angle(landmarks, side=side, min_vis=min_vis)
    knee_angle  = calculate_knee_angle(landmarks,  side=side, min_vis=min_vis)

    metrics = {
        "elbow_avg": float(elbow_angle) if elbow_angle == elbow_angle else float("nan"),
        "knee_avg":  float(knee_angle)  if knee_angle  == knee_angle  else float("nan"),
    }

    # 4) 진단: thresholds 규칙 적용 (+ elbow 텍스트 백업)
    diagnosis = _apply_bins_metrics_dict(metrics)
    elbow_feedback = generate_feedback(elbow_angle)

    if elbow_feedback and 'elbow_diag' not in diagnosis:
        diagnosis['elbow_diag'] = elbow_feedback

    # 5) 검출률 계산
    detected = len(landmarks)           # 검출 성공 프레임 수
    total = int(total_seen or detected) # 샘플링 후 총 평가 프레임 수
    rate = round(detected / total, 3) if total else None

    swing_id = os.path.basename(file_path).split("_")[0]

    # 6) 내부 로깅(full_result): ML/튜닝/리포팅용
    full_result = {
        "swingId": swing_id,
        "side": side,
        "min_vis": min_vis,
        "preprocessMode": used_mode,
        "preprocessMs": preprocess_ms,
        "detectedFrames": detected,
        "totalFrames": total,
        "detectionRate": rate,
        "metrics": metrics,
        "diagnosis": diagnosis,
        # TODO: phases, framewise series 등 확장 가능
    }
    try:
        log_path = os.path.join(_LOG_DIR, f"{swing_id}_{uuid.uuid4().hex[:6]}.json")
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(full_result, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.debug(f"[LOG] write failed: {e}")

    # 7) 최종 응답
    return full_result

def analyze_from_url(s3_url: str, side: str = "right", min_vis: float = 0.5,
                     norm_mode: NormMode = NormMode.auto) -> dict:
    """
    원격 URL(S3 등)에서 파일을 받아 analyze_swing으로 위임.
    - stream=True로 메모리 사용을 줄이고 파일로 직접 저장.
    """
    os.makedirs("downloads", exist_ok=True)
    filename = f"downloads/{uuid.uuid4().hex[:8]}.mp4"
    with requests.get(s3_url, stream=True) as r:
        r.raise_for_status()
        with open(filename, "wb") as f:
            shutil.copyfileobj(r.raw, f)
            
    return analyze_swing(filename, side=side, min_vis=min_vis, norm_mode=norm_mode)