# app/analyze/service.py
from __future__ import annotations

import os, shutil, uuid, time, json, requests, logging
from typing import Optional, Dict, Any, List

from fastapi import HTTPException

from app.analyze.extractor import PoseExtractor
from app.analyze.angle import calculate_elbow_angle, calculate_knee_angle, angles_at_frame
from app.analyze.phase import detect_phases
from app.analyze.schema import NormMode, ClubType
from app.config.settings import settings
from app.analyze.preprocess import normalize_video, normalize_video_pro
from app.analyze.results_builder import build_result
from app.analyze.diagnosis import build_phase_diagnosis
from app.utils.resource_finder import rf

# ---------- 로거 ----------
logger = logging.getLogger(__name__)
if not logging.getLogger().handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

# ---------- 내부 로깅 디렉토리 ----------
_LOG_DIR = settings.LOG_DIR
_LOG_DIR.mkdir(parents=True, exist_ok=True)

# ---------- 메인 파이프라인 ----------
def analyze_swing(
    file_path: str,
    side: str = "right",
    min_vis: float = 0.5,
    norm_mode: NormMode = NormMode.auto,
    club: Optional[ClubType] = None
) -> dict:
    """
    1) 전처리 → 2) 포즈 추출 → 3) 평균 메트릭 계산 → 4) 페이즈별 메트릭 → 5) 페이즈별 진단 → 6) 로깅/응답
    """
    # 1) 전처리
    try:
        norm_path, used_mode, preprocess_ms = _do_preprocess(file_path, norm_mode)
        norm_path = str(norm_path)
    except FileNotFoundError as e:
        raise HTTPException(status_code=422, detail=f"Input not found: {e}")
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=f"Preprocess failed: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")

    # 2) 포즈 추출
    extractor = PoseExtractor(step=getattr(settings, "POSE_FRAME_STEP", 3))
    landmarks_np, landmarks, total_seen = extractor.extract_from_video(norm_path)

    # 3) (선택) 평균 메트릭
    elbow_angle = calculate_elbow_angle(landmarks, side=side, min_vis=min_vis)
    knee_angle  = calculate_knee_angle(landmarks, side=side, min_vis=min_vis)
    metrics = {
        "elbow_avg": float(elbow_angle) if elbow_angle == elbow_angle else float("nan"),
        "knee_avg":  float(knee_angle)  if knee_angle  == knee_angle  else float("nan"),
    }

    # 4) 페이즈별 지표
    phase_method = getattr(settings, "PHASE_METHOD", "auto")
    phases = detect_phases(landmarks, phase_method)

    # 동알 페이즈 인덱스 중복 제거(P2 → P9 우선 채택)
    phases = _dedupe_phases(phases)

    phase_metrics: Dict[str, Dict[str, float]] = {}
    for key, idx in phases.items():
        if idx is None or idx >= len(landmarks):
            phase_metrics[key] = {}
            continue
        frame = landmarks[idx]
        phase_metrics[key] = angles_at_frame(frame, side=side)

    # 5) thresholds 로드 & 페이즈별 진단
    thresholds = _load_thresholds()

    # settings.THRESH_METRICS가 있으면 사용, 없으면 관측된 키로 도출
    metrics_for_label: List[str] = getattr(settings, "THRESH_METRICS", None) or _infer_metrics_from_phase(phase_metrics)

    club_key = club.value if hasattr(club, "value") else (club or "")
    diagnosis_by_phase = build_phase_diagnosis(
        phase_metrics=phase_metrics,
        club=club_key,
        thresholds=thresholds,
        metrics=metrics_for_label,
    )

    # 6) 검출률/응답
    detected = len(landmarks)
    total = int(total_seen or detected)
    rate = round(detected / total, 3) if total else None
    swing_id = os.path.basename(file_path).split("_")[0]

    result = build_result(
        swing_id=swing_id,
        file_path=file_path,
        side=side,
        club=club,
        used_mode=used_mode,
        preprocess_ms=preprocess_ms,
        min_vis=min_vis,
        phase_method=phase_method,
        detected=detected,
        total=total,
        rate=rate,
        metrics=metrics,            # FE가 안 쓰면 results_builder에서 빼도 OK
        phases=phases,
        phase_metrics=phase_metrics,
        diagnosis_by_phase=diagnosis_by_phase,  # 페이즈별만 (AVG 없음)
    )

    # 내부 로깅
    try:
        log_path = settings.LOG_DIR / f"{swing_id}_{uuid.uuid4().hex[:6]}.json"
        with log_path.open("w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii = False, indent = 2)
    except Exception as e:
        logger.debug(f"[LOG] write failed: {e}")

    return result


def analyze_from_url(
    s3_url: str,
    side: str = "right",
    min_vis: float = 0.5,
    norm_mode: NormMode = NormMode.auto
) -> dict:
    dst_dir = settings.DOWNLOADS_DIR
    dst_dir.mkdir(parents = True, exist_ok = True)
    filename = f"downloads/{uuid.uuid4().hex[:8]}.mp4"

    with requests.get(s3_url, stream=True) as r:
        r.raise_for_status()
        with open(filename, "wb") as f:
            shutil.copyfileobj(r.raw, f)
    return analyze_swing(str(filename), side=side, min_vis=min_vis, norm_mode=norm_mode)


# ------------ Private ------------
def _infer_metrics_from_phase(phase_metrics: Dict[str, Dict[str, float]]) -> list:
    """설정이 없을 때, 관측된 페이즈 항목들에서 metric 키 합집합을 만든다."""
    keys = set()
    for vals in phase_metrics.values():
        keys.update(vals.keys())
    return sorted(keys)


def _load_thresholds() -> dict:
    """
    thresholds 우선순위:
      1) ENV THRESHOLDS_FILE 지정
      2) app/config/thresholds_current.json (심링크)
      3) app/config/*_thresholds.json 중 mtime 최신본
    """
    path = rf.thresholds_path()
    if not path.exists():
        logger.warning(f"[THRESH] thresholds file not found: {path}")
        return {}
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        logger.info(f"[THRESH] loaded: {path}")
        return data if isinstance(data, dict) else {}
    except Exception as e:
        logger.warning(f"[THRESH] failed to load {path}: {e}")
        return {}


def _do_preprocess(src_path: str, mode: NormMode):
    """
    입력 영상 표준화:
      - basic: 재인코딩
      - pro: HW 인코딩/스마트카피
      - auto: pro→실패시 basic
    """
    dst_dir = settings.NORMALIZED_DIR
    dst_dir.mkdir(parents=True, exist_ok=True)
    dst_path = dst_dir / f"{uuid.uuid4().hex[:8]}.mp4"

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
        else:
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

    return str(dst_path), used_mode, ms


def _dedupe_phases(phases: Dict[str, int]) -> Dict[str, int]:
    """
    서로 다른 페이즈가 같은 프레임 인덱스를 가리키는 경우를 정리.
    정책: 앞 순서(P2→P9) 우선 채택, 중복 인덱스가 뒤에서 나오면 버림.
    """
    order = ["P2","P3","P4","P5","P6","P7","P8","P9"]
    seen = set()
    out: Dict[str, int] = {}
    for p in order:
        idx = phases.get(p)
        if idx is None:
            continue
        if idx in seen:
            continue
        seen.add(idx)
        out[p] = idx
    return out