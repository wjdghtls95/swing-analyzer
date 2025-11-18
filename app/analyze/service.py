from __future__ import annotations
from fastapi import HTTPException
import os, shutil, uuid, time, json, requests, logging, glob
from typing import Optional, Dict, List, Tuple, Any
from pathlib import Path

from app.analyze.extractor import PoseExtractor
from app.analyze.angle import (
    calculate_elbow_angle,
    calculate_knee_angle,
    angles_at_frame,
)
from app.analyze.phase import detect_phases
from app.analyze.schema import NormMode, ClubType
from app.analyze.preprocess import normalize_video, normalize_video_pro
from app.analyze.results_builder import build_result
from app.analyze.diagnosis import build_phase_diagnosis

from app.config.settings import settings

from app.llm.client import LLMGatewayClient

from app.utils.resource_finder import rf
from app.utils.thresholds_utils import (
    qc_thresholds_usable,
    adapt_bins_to_ranges,
)

_llm = LLMGatewayClient()

# ---------- 로거 ----------
logger = logging.getLogger(__name__)
if not logging.getLogger().handlers:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )

# ---------- 내부 로깅 디렉토리 ----------
_LOG_DIR = settings.LOG_DIR
_LOG_DIR.mkdir(parents=True, exist_ok=True)

# REQUIRED_KEYS는 settings 에서만 관리
REQUIRED_KEYS = set(settings.THRESH_REQUIRED_KEYS)


# ---------- 메인 파이프라인 ----------
def analyze_swing(
        file_path: str,
        side: str = "right",
        min_vis: float = 0.5,
        norm_mode: NormMode = NormMode.auto,
        club: Optional[ClubType] = None,
        llm_config: Optional[dict] = None
) -> dict:
    """
    파이프 라인
    1) 전처리 → 2) 포즈 추출 → 3) 평균 메트릭 계산 → 4) 페이즈별 지표 → 5) thresholds 로딩/적용 → 6) 룰 기반 진단 -> 7) LLM 요약/행동 가이드 -> 8) 응답
    """
    llm_config = llm_config or {}
    llm_provider = llm_config.get('provider')

    # 이 llm_extra가 (플로우 6번) llm gateway로 전달될 옵션
    llm_extra = {k: v for k, v in llm_config.items() if k != "provider"}

    # 1) 전처리 (영상 표준화)
    try:
        norm_path, used_mode, preprocess_ms = _do_preprocess(file_path, norm_mode)
        norm_path = str(norm_path)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=f"Input not found: {e}")
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=f"Preprocess failed: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")

    # 2) 포즈 추출
    extractor = PoseExtractor(step=getattr(settings, "POSE_FRAME_STEP", 3))
    landmarks_np, landmarks, total_seen = extractor.extract_from_video(norm_path)

    # 3) 평균 메트릭
    elbow_angle = calculate_elbow_angle(landmarks, side=side, min_vis=min_vis)
    knee_angle = calculate_knee_angle(landmarks, side=side, min_vis=min_vis)
    metrics = {
        "elbow_avg": float(elbow_angle) if elbow_angle == elbow_angle else float("nan"),
        "knee_avg": float(knee_angle) if knee_angle == knee_angle else float("nan"),
    }

    # 4) 페이즈별 지표
    phase_method = settings.PHASE_METHOD
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

    # 5) thresholds 로드 / 변환 /페이즈별 진단
    # thresholds = _load_thresholds()
    thresholds_raw = _load_thresholds(by="phase")
    thresholds_for_rules = _adapt_thresholds_bins_to_ranges(
        thresholds_raw, qlow=settings.THRESH_QLOW, qhigh=settings.THRESH_QHIGH
    )

    # settings.THRESH_METRICS가 있으면 사용, 없으면 관측된 키로 도출
    metrics_for_label: List[str] = settings.THRESH_METRICS or _infer_metrics_from_phase(
        phase_metrics
    )

    club_key = club.value if hasattr(club, "value") else (club or "")
    diagnosis_by_phase = build_phase_diagnosis(
        phase_metrics=phase_metrics,
        club=club_key,
        thresholds=thresholds_for_rules,
        metrics=metrics_for_label,
    )

    try:
        logger.info(f"[DEBUG] phase_metrics: {json.dumps(phase_metrics, indent=2)}")
    except Exception:
        logger.info(f"[DEBUG] phase_metrics (non-serializable): {phase_metrics}")

    try:
        logger.info(f"[DEBUG] diagnosis_by_phase: {json.dumps(diagnosis_by_phase, indent=2)}")
    except Exception:
        logger.info(f"[DEBUG] diagnosis_by_phase (non-serializable): {diagnosis_by_phase}")

    # 6) LLM 요약 (gateway / sdk 모두 Delegate에 위임)
    #   - 프롬프트도 하드코딩 금지하고 싶다면 settings에 상수로 빼서 관리 가능
    feedback = None

    if llm_provider == 'gateway':
        try:
            analysis_data = _map_to_delegate_dto(
                swing_id=os.path.basename(file_path).split("_")[0],
                side=side,
                club=club_key,
                phases=phases,
                phase_metrics=phase_metrics,
                diagnosis_by_phase=diagnosis_by_phase,
            )

            feedback = _llm.chat_summary_gateway(
                analysis_data=analysis_data,
                **llm_extra
            )

            logger.info(f"[LLM] gateway feedback: {feedback}")

        except Exception as e:
            logger.warning(f"[LLM] gateway call failed: {e}")
            feedback = f"Error: LLM Gateway call failed ({e})"

    # 7) 응답 조립
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
        metrics=metrics,  # FE가 안 쓰면 results_builder에서 빼도 OK
        phases=phases,
        phase_metrics=phase_metrics,
        diagnosis_by_phase=diagnosis_by_phase,  # 페이즈별만 (AVG 없음)
    )

    # 내부 로깅
    try:
        log_path = settings.LOG_DIR / f"{swing_id}_{uuid.uuid4().hex[:6]}.json"
        log_path.write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except Exception as e:
        logger.debug(f"[LOG] write failed: {e}")

    if feedback:
        result["feedback"] = feedback

    return result


# 사용하는 DTO 변환 함수이므로 반드시 유지
def _map_to_delegate_dto(
        phases: Dict[str, int],
        phase_metrics: Dict[str, Dict[str, float]],
        diagnosis_by_phase: Dict[str, Any],
        swing_id: str,
        side: str,
        club: str,
) -> dict:
    analysis_data = {
        "swing_id": swing_id,
        "side": side,
        "club": club,
        "phases": phases,
        "phase_metrics": phase_metrics,
        "diagnosis_by_phase": diagnosis_by_phase,
    }

    return analysis_data


# s3 도입시 사용할 service 단 코드
def analyze_from_url(
        s3_url: str,
        side: str = "right",
        min_vis: float = 0.5,
        norm_mode: NormMode = NormMode.auto,
        llm_config: Optional[dict] = None
) -> dict:
    """S3/HTTP 동영상 다운로드 후 동일 파이프라인 수행"""
    downloads = settings.DOWNLOADS_DIR
    downloads.mkdir(parents=True, exist_ok=True)

    filename = f"downloads/{uuid.uuid4().hex[:8]}.mp4"

    with requests.get(s3_url, stream=True) as r:
        r.raise_for_status()
        with open(filename, "wb") as f:
            shutil.copyfileobj(r.raw, f)

    return analyze_swing(
        str(filename),
        side=side,
        min_vis=min_vis,
        norm_mode=norm_mode,
        llm_config=llm_config
    )


# ------------ Private ------------
def _infer_metrics_from_phase(phase_metrics: Dict[str, Dict[str, float]]) -> list:
    """설정이 없을 때, 관측된 페이즈 항목들에서 metric 리스트 생성"""
    keys = set()
    for vals in phase_metrics.values():
        keys.update(vals.keys())
    return sorted(keys)


def _recent_threshold_candidates() -> list[Path]:
    """CONFIG_DIR 아래 *_thresholds.json 중 current가 가리키는 실제 파일을 제외하고 최신순으로 반환"""
    base = settings.CONFIG_DIR
    current = base / "thresholds_current.json"

    try:
        current_real = current.resolve(strict=True) if current.exists() else None
    except Exception:
        current_real = None

    pattern = str(base / "*_thresholds.json")
    paths = [Path(p) for p in glob.glob(pattern)]
    paths = [p for p in paths if p.is_file()]

    if current_real:
        paths = [p for p in paths if p.resolve() != current_real]
    paths.sort(key=lambda p: p.stat().st_mtime, reverse=True)

    return paths


def _by_view(data: dict, by: Optional[str]) -> dict:
    """파일 구조(by='phase'|'club'|'overall')에 맞춰 서브뷰 반환"""
    if by is None:
        return data
    by = str(by).lower()
    if by == "overall":
        return data.get("overall") or data
    elif by in ("phase", "club"):
        return data
    return data


# Thresholds 로딩
# 1) current fhem -> qc 통과시 사용
# 2) 실패 시 최근본 순회하면서 처음본 통과본 사용
# 3) 모두 실패시 dict return
def _load_thresholds(by: Optional[str] = None) -> dict:
    """
    thresholds_current.json(또는 최신본)에서 by 섹션('phase'|'club'|'overall') 형태를 반환.
    파일 구조는 생성 스크립트에 따라:
      - by=phase:  { "P2": {...}, "P3": {...}, ... }
      - by=club:   { "iron": {...}, "driver": {...}, ... }
      - by=overall:{ "overall": {...} }
    """
    # 1. resource_finder를 통해 올바른 thresholds 파일 경로 탐색
    path = rf.thresholds_path()
    data = {}

    if not path or not path.exists():
        logger.warning(f"[THRESH] No thresholds file found by resource_finder (path: {path}).")
        return {}

    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception as e:
        logger.warning(f"[THRESH] failed to load current {path}: {e}")

    # 2. utils의 표준 QC 함수 사용
    if qc_thresholds_usable(data, REQUIRED_KEYS):
        return _by_view(data, by)

    logger.warning("[THRESH] current unusable. trying recent archives...")

    # 3. QC 실패 시 아카이브에서 최신본 탐색 (기존 로직 유지)
    for cand in _recent_threshold_candidates():
        try:
            cand_data = json.loads(cand.read_text(encoding="utf-8"))
        except Exception as e:
            logger.warning(f"[THRESH] skip {cand.name}: load error {e}")
            continue

        # 3-1. utils의 표준 QC 함수 사용
        if qc_thresholds_usable(cand_data, REQUIRED_KEYS):
            logger.info(f"[THRESH] fallback -> {cand.name}")
            return _by_view(cand_data, by)

    logger.error("[THRESH] no usable thresholds found. use empty.")
    return {}


# bins → min / max 어댑트 (룰 호환)
def _range_from_bins(
        block: dict, qlow: float, qhigh: float
) -> Optional[Tuple[float, float]]:
    """bins 엣지를 퍼센타일 구간으로 변환 (settings.THRESH_QLOW/HIGH 사용)"""
    if not isinstance(block, dict) or not REQUIRED_KEYS.issubset(block.keys()):
        return None

    bins = block.get("bins")

    if not isinstance(bins, list) or len(bins) < 2:
        return None

    if len(bins) == 2:
        return float(bins[0]), float(bins[1])

    m = len(bins)
    lo_idx = max(0, min(m - 1, int(qlow * (m - 1))))
    hi_idx = max(0, min(m - 1, int(qhigh * (m - 1))))
    lo = float(bins[min(lo_idx, hi_idx)])
    hi = float(bins[max(lo_idx, hi_idx)])

    if lo == hi:
        return None

    return lo, hi


def _adapt_thresholds_bins_to_ranges(thr: dict, qlow: float, qhigh: float) -> dict:
    """중첩 구조(phase/club/overall) 내 metric block들을 {min,max}로 변환"""
    return adapt_bins_to_ranges(thr, qlow=qlow, qhigh=qhigh, required_keys=REQUIRED_KEYS)


# 입력 영상 표준화
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
            normalize_video_pro(
                src_path, dst_path, fps=fps, height=height, mirror=mirror
            )
            used_mode = "pro"
        else:
            try:
                normalize_video_pro(
                    src_path, dst_path, fps=fps, height=height, mirror=mirror
                )
                used_mode = "pro"
            except Exception:
                normalize_video(
                    src_path, dst_path, fps=fps, height=height, mirror=mirror
                )
                used_mode = "basic"

    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=f"input not found: {e}") from e

    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=f"preprocess failed: {e}") from e

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"unexpected preprocess error: {e}"
        ) from e

    finally:
        ms = int((time.perf_counter() - t0) * 1000)

    return str(dst_path), used_mode, ms


def _dedupe_phases(phases: Dict[str, int]) -> Dict[str, int]:
    """
    서로 다른 페이즈가 같은 프레임 인덱스를 가리키는 경우를 정리.
    정책: 앞 순서(P2→P9) 우선 채택, 중복 인덱스가 뒤에서 나오면 버림.
    """
    order = settings.THRESH_PHASES
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
