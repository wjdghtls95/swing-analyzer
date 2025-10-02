from typing import Dict, List, Any, Optional
import logging
import os

import numpy as np

from app.config.settings import settings
from app.analyze.angle import angles_at_frame  # 프레임 단위 elbow/knee/spine_tilt 계산

logger = logging.getLogger(__name__)

# Public API
def detect_phases(
    landmarks: List[List[Dict[str, Any]]],
    method: str = "auto",
) -> Dict[str, Optional[int]]:
    """
    P2~P9 키프레임 인덱스 검출.
    - method: "auto" | "ml" | "rule"
      * "auto": 모델이 로드되면 ML, 없으면 rule(equal-split) fallback
      * "ml":   모델 없으면 rule로 강제 fallback (warning 로그)
      * "rule": 항상 rule(equal-split)
    반환: {"P2": idx_or_None, ..., "P9": idx_or_None}
    """
    total = len(landmarks)
    if total < 9:
        return {f"P{i}": None for i in range(2, 10)}

    if method == "rule":
        return _detect_phases_equal_split(total)

    if method in ("auto", "ml"):
        model = _load_phase_model()  # None일 수 있음(미배포)
        if model is not None:
            try:
                return _predict_phase_indices_ml(landmarks, model)
            except Exception as e:
                logger.warning(f"[phase] ML inference failed, fallback to rule: {e}")

        if method == "ml":
            logger.warning("[phase] ML requested but model not available; falling back to rule.")

        # fallback
        return _detect_phases_equal_split(total)

    # 안전장치: 정의되지 않은 method → rule
    logger.warning(f"[phase] unknown method={method}, fallback to rule.")
    return _detect_phases_equal_split(total)


# Private helpers
def _detect_phases_equal_split(total_frames: int) -> Dict[str, int]:
    """
    데모/폴백용: 전체 프레임을 8등분하여 P2~P9 인덱스 산출.
    """
    step = total_frames // 8
    return {f"P{i}": step * (i - 2) for i in range(2, 10)}


# ---- ML 로딩/추론 ------------------------------------------------------------

_PHASE_MODEL = None  # lazy cache

def _load_phase_model():
    """
    Phase 모델 지연 로딩.
    - settings.PHASE_MODEL_PATH 또는 ENV PHASE_MODEL_PATH를 우선 사용.
    - 파일 없거나 로드 실패 시 None 반환(서비스는 rule로 폴백).
    """
    global _PHASE_MODEL
    if _PHASE_MODEL is not None:
        return _PHASE_MODEL

    # 우선순위: settings -> env
    path = getattr(settings, "PHASE_MODEL_PATH", None) or os.environ.get("PHASE_MODEL_PATH")
    if not path:
        return None

    if not os.path.exists(path):
        logger.warning(f"[phase] model path not found: {path}")
        return None

    try:
        import pickle
        with open(path, "rb") as f:
            _PHASE_MODEL = pickle.load(f)
        logger.info(f"[phase] model loaded: {path}")
        return _PHASE_MODEL
    except Exception as e:
        logger.warning(f"[phase] model load failed: {e}")
        return None


def _predict_phase_indices_ml(
    landmarks: List[List[Dict[str, Any]]],
    model,
) -> Dict[str, Optional[int]]:
    """
    간이 ML 추론 스텁:
      1) 프레임별 특징(각도/차분 등) 계산 → (T, F)
      2) 모델로 frame-wise 점수/클래스 예측(가정)
      3) 각 Phase의 피크/최댓값 인덱스를 키프레임으로 선택

    참고: 실제 모델/학습 파이프라인에 맞게 바꿔도 detect_phases 퍼블릭 인터페이스는 그대로
    """
    X = _featurize_sequence(landmarks)  # (T, F)
    if X.size == 0:
        return _detect_phases_equal_split(len(landmarks))

    # 예시 1) 다중 이진 분류를 dict로 제공하는 모델 가정:
    #   scores = model.predict_proba_dict(X)["P4"] ... 이런 형태라면 그대로 최대값 argmax
    # 예시 2) 멀티클래스(프레임→{P2..P9..None})라면 각 클래스로 argmax 인덱스 추출
    # 여기선 멀티클래스 argmax를 가정한 최소 구현(클래스 라벨이 "P2".."P9" 문자열이라고 가정)
    try:
        # scikit-learn의 predict_proba: shape (T, C). classes_에 레이블.
        # 없으면 predict로 대체.
        if hasattr(model, "predict_proba"):
            proba = model.predict_proba(X)  # (T, C)
            classes = list(getattr(model, "classes_", []))
            if not classes:
                # 일부 라이브러리는 classes_ 대신 model.metadata 등에 둘 수 있음
                # 없으면 predict로 폴백
                preds = model.predict(X)
                return _indices_from_sequence_labels(preds)
            # 각 phase별 argmax
            return _indices_from_multiclass_proba(proba, classes)
        else:
            preds = model.predict(X)  # (T,)
            return _indices_from_sequence_labels(preds)
    except Exception as e:
        logger.warning(f"[phase] model inference error: {e}")
        return _detect_phases_equal_split(len(landmarks))


def _featurize_sequence(landmarks: List[List[Dict[str, Any]]]) -> np.ndarray:
    """
    프레임별 기본 피처:
      [elbow, knee, spine_tilt, d_elbow, d_knee, d_spine, dd_elbow, dd_knee, dd_spine]
    """
    T = len(landmarks)
    if T == 0:
        return np.empty((0, 0), dtype=float)

    arr = np.zeros((T, 3), dtype=float)
    for t in range(T):
        vals = angles_at_frame(landmarks[t], side="right")  # side는 서비스에서 일관되게 전달됨
        arr[t, 0] = vals.get("elbow") or np.nan
        arr[t, 1] = vals.get("knee") or np.nan
        arr[t, 2] = vals.get("spine_tilt") or np.nan

    # NaN 보정(전방채움 → 후방채움 → 0)
    for j in range(arr.shape[1]):
        col = arr[:, j]
        # forward fill
        mask = np.isnan(col)
        if mask.any():
            valid_idx = np.where(~mask)[0]
            if valid_idx.size > 0:
                first = valid_idx[0]
                col[:first] = col[first]
                for k in range(first + 1, T):
                    if np.isnan(col[k]):
                        col[k] = col[k - 1]
                arr[:, j] = col

    arr = np.nan_to_num(arr, nan=0.0)

    # 1차/2차 차분
    d1 = np.vstack([np.zeros((1, 3)), np.diff(arr, axis=0)])
    d2 = np.vstack([np.zeros((1, 3)), np.diff(d1, axis=0)])

    X = np.concatenate([arr, d1, d2], axis=1)  # (T, 9)
    return X.astype(np.float32)


def _indices_from_sequence_labels(preds: np.ndarray) -> Dict[str, Optional[int]]:
    """
    프레임별 멀티클래스 예측(예: ["P2","None","None","P3",...])에서
    각 P2..P9의 최초 등장 또는 최대 스코어 위치를 선정(여기선 최초 등장).
    """
    out = {f"P{i}": None for i in range(2, 10)}
    for t, lab in enumerate(preds):
        if isinstance(lab, bytes):
            lab = lab.decode("utf-8", "ignore")
        if isinstance(lab, (str,)):
            if lab.startswith("P") and lab[1:].isdigit():
                if lab in out and out[lab] is None:
                    out[lab] = t
    # 못 찾은 것은 간단 보정(equal-split)
    for k, v in out.items():
        if v is None:
            # total length가 필요 → preds 길이 사용
            total = len(preds)
            out.update(_detect_phases_equal_split(total))
            break
    return out


def _indices_from_multiclass_proba(proba: np.ndarray, classes: List[str]) -> Dict[str, Optional[int]]:
    """
    (T,C) proba와 클래스 라벨 리스트가 주어졌을 때,
    각 P2..P9 클래스의 argmax 프레임을 반환.
    """
    out = {f"P{i}": None for i in range(2, 10)}
    for p in range(2, 10):
        cls = f"P{p}"
        if cls not in classes:
            continue
        cidx = classes.index(cls)
        argmax = int(np.argmax(proba[:, cidx])) if proba.shape[0] else None
        out[cls] = argmax
    # 못 찾은 클래스가 있으면 equal-split 보정
    if any(v is None for v in out.values()):
        total = proba.shape[0]
        out.update(_detect_phases_equal_split(total))
    return out