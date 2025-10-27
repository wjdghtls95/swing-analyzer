from __future__ import annotations
from fastapi import HTTPException
import os, shutil, uuid, time, json, requests, logging, glob
from typing import Optional, Dict, List, Tuple
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

from app.llm.client import DelegateLLMClient

from app.utils.resource_finder import rf
from app.utils.types.types import Message
from app.utils.thresholds_utils import (
    qc_thresholds_usable,
    adapt_bins_to_ranges,
)

_llm = DelegateLLMClient()

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
    # LLM 옵션: 기본값/체인/토큰 등은 settings 에서만 관리
    llm_provider: str = settings.LLM_DEFAULT_PROVIDER,
    llm_model: Optional[str] = None,
    llm_api_key: Optional[str] = None,
    llm_extra: Optional[Dict[str, any]] = None,
) -> dict:
    """
    파이프 라인
    1) 전처리 → 2) 포즈 추출 → 3) 평균 메트릭 계산 → 4) 페이즈별 지표 → 5) thresholds 로딩/적용 → 6) 룰 기반 진단 -> 7) LLM 요약/행동 가이드 -> 8) 응답
    """
    llm_extra = llm_extra or {}

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

    # 6) LLM 요약 (gateway / compat / sdk 모두 Delegate에 위임)
    #   - 프롬프트도 하드코딩 금지하고 싶다면 settings에 상수로 빼서 관리 가능
    system_prompt = (
        "You are a concise golf swing coach. "
        "Explain issues briefly and list up to 3 actionable steps. "
        "Keep each action under 15 words."
    )
    user_prompt = (
        "Phase-based diagnosis JSON (already evaluated by thresholds):\n"
        f"{json.dumps(diagnosis_by_phase, ensure_ascii=False)}\n\n"
        f"Side: {side}, Club: {club_key or 'unknown'}\n"
        "Return:\n- summary: 1-2 sentences\n- actions: bullet points (<=3)"
    )

    messages: List[Message] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    delegate_provider, delegate_extra = _map_to_delegate(llm_provider, llm_extra)

    try:
        llm_text = _llm.generate(
            messages,
            provider=llm_provider,
            model=(llm_model or settings.LLM_DEFAULT_MODEL),
            temperature=settings.LLM_TEMPERATURE_DEFAULT,
            max_tokens=settings.LLM_MAX_TOKENS_DEFAULT,
            timeout=20.0,
            api_key_override=llm_api_key,
            extra=delegate_extra,
        )
    except Exception as e:
        logger.warning(f"[LLM] failed: {e}")
        llm_text = "[LLM unavailable]"

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

    result["feedback"] = {
        "summary": llm_text,
        "provider": llm_provider,
        "model": (llm_model or settings.LLM_DEFAULT_MODEL),
    }

    return result


def _map_to_delegate(
    provider: str, extra: Dict[str, any]
) -> Tuple[str, Dict[str, any]]:
    """
    Router로부터 받은 provider/vendor를 Delegate가 이해하는 형태로 어댑트.
    - "gateway": 게이트웨이로 포워딩 (vendor는 extra["vendor"]에 포함되어 들어옴)
    - "compat" : OpenAI-호환 REST (base_url/api_key 필요)
    - "openai":  SDK 경유
    - 그 외     : gateway로 폴백
    """
    vendor = extra.get("vendor", "openai")
    if provider == "gateway":
        return "gateway", {"vendor": vendor, **extra}
    if provider == "compat":
        return "compat", {"vendor": vendor, **extra}
    if provider == "openai":
        return "openai", {**extra}
    return "gateway", {"vendor": vendor, **extra}


# s3 도입시 사용할 service 단 코드
def analyze_from_url(
    s3_url: str,
    side: str = "right",
    min_vis: float = 0.5,
    norm_mode: NormMode = NormMode.auto,
    llm_provider: str = settings.LLM_DEFAULT_PROVIDER,
    llm_model: Optional[str] = None,
    llm_api_key: Optional[str] = None,
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
        llm_provider=llm_provider,
        llm_model=llm_model,
        llm_api_key=llm_api_key,
    )


# ------------ Private ------------
def _infer_metrics_from_phase(phase_metrics: Dict[str, Dict[str, float]]) -> list:
    """설정이 없을 때, 관측된 페이즈 항목들에서 metric 리스트 생성"""
    keys = set()
    for vals in phase_metrics.values():
        keys.update(vals.keys())
    return sorted(keys)


# 런타임 QC + 폴백 (bins 스키마 기준)
def _has_metric_block_like(d: dict) -> bool:
    """말단에 settings.THRESH_REQUIRED_KEYS 구조를 만족하는 블록이 존재하는지 검사"""
    if not isinstance(d, dict):
        return False
    if REQUIRED_KEYS.issubset(d.keys()):
        return True
    for v in d.values():
        if isinstance(v, dict) and _has_metric_block_like(v):
            return True
    return False


def _is_thresholds_usable(data: dict) -> bool:
    """가벼운 런타임 QC: empty/잘못된 bins/음수 n 등 최소한의 체크"""
    if not isinstance(data, dict) or not data:
        return False
    if not _has_metric_block_like(data):
        return False

    ok_bins = False
    ok_n = False

    def _walk(d: dict):
        nonlocal ok_bins, ok_n
        for _, v in d.items():
            if isinstance(v, dict) and REQUIRED_KEYS.issubset(v.keys()):
                bins = v.get("bins", [])
                if isinstance(bins, list) and len(bins) >= 2:
                    if all(isinstance(b, (int, float)) for b in bins):
                        if all(bins[i] >= bins[i - 1] for i in range(1, len(bins))):
                            ok_bins = True
                n = v.get("n", None)
                if isinstance(n, int) and n >= 0:
                    ok_n = True
            elif isinstance(v, dict):
                _walk(v)

    _walk(data)
    return ok_bins and ok_n


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
    path = rf.thresholds_path()
    data = {}
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception as e:
        logger.warning(f"[THRESH] failed to load current {path}: {e}")

    if qc_thresholds_usable(data, REQUIRED_KEYS):
        return _by_view(data, by)

    logger.warning("[THRESH] current unusable. trying recent archives...")

    for cand in _recent_threshold_candidates():
        try:
            cand_data = json.loads(cand.read_text(encoding="utf-8"))
        except Exception as e:
            logger.warning(f"[THRESH] skip {cand.name}: load error {e}")
            continue
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

    def _walk(src: dict) -> dict:
        local = {}
        for k, v in src.items():
            if isinstance(v, dict) and REQUIRED_KEYS.issubset(v.keys()):
                rng = _range_from_bins(v, qlow, qhigh)
                if rng:
                    local[k] = {"min": rng[0], "max": rng[1]}
            elif isinstance(v, dict):
                nested = _walk(v)
                if nested:
                    local[k] = nested
        return local

    return _walk(thr)


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