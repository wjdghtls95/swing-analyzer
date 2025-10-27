from __future__ import annotations
from typing import Dict, Any, Callable, Optional, Tuple
from functools import partial

# ─────────────────────────────────────────
# 기본 판별/순회 유틸
# ─────────────────────────────────────────


def is_metric_block(d: Dict[str, Any], required_keys: set[str]) -> bool:
    """
    주어진 dict가 '메트릭 블록' 형태인지 확인
    - 메트릭 블록: {"bins": [...], "mean": ..., "std": ..., "n": ...}
    - required_keys: 예) {"bins", "mean", "std", "n"}
    """
    return isinstance(d, dict) and required_keys.issubset(d.keys())


def walk_dict(
    d: Dict[str, Any],
    *,
    on_block: Callable[[Dict[str, Any], Tuple[str, ...]], None],
    required_keys: set[str],
    path: Optional[Tuple[str, ...]] = None,
) -> None:
    """
    thresholds JSON(중첩 dict)을 DFS로 순회하며, '메트릭 블록'을 만날 때마다 on_block 호출.
    - on_block(block, path): block은 메트릭 블록(dict), path는 루트→현재까지의 경로 튜플
    """
    if path is None:
        path = tuple()
    if is_metric_block(d, required_keys):
        on_block(d, path)
        return
    for k, v in d.items():
        if isinstance(v, dict):
            walk_dict(
                v, on_block=on_block, required_keys=required_keys, path=path + (str(k),)
            )


# ─────────────────────────────────────────
# 가벼운 Quality Check (중첩함수 제거: 전역 콜백 + partial 로 상태 주입)
# ─────────────────────────────────────────


def _qc_on_block(
    state: Dict[str, bool],
    block: Dict[str, Any],
    _path: Tuple[str, ...],
) -> None:
    """
    QC용 전역 콜백: bins/n 검사 결과를 state dict에 누적.
    - state: {"ok_bins": bool, "ok_n": bool}
    """
    bins = block.get("bins", [])
    if (
        isinstance(bins, list)
        and len(bins) >= 2
        and all(isinstance(b, (int, float)) for b in bins)
    ):
        if all(bins[i] >= bins[i - 1] for i in range(1, len(bins))):
            state["ok_bins"] = True

    n = block.get("n")
    if isinstance(n, int) and n >= 0:
        state["ok_n"] = True


def qc_thresholds_usable(data: Dict[str, Any], required_keys: set[str]) -> bool:
    """
    '가벼운 QC' 판정:
      - 최소 하나 이상의 유효 bins(오름차순 엣지, 길이>=2) 존재?
      - 최소 하나 이상의 유효 n(0 이상 정수) 존재?
    둘 다 True 면 사용 가능.
    """
    if not isinstance(data, dict) or not data:
        return False

    state: Dict[str, bool] = {"ok_bins": False, "ok_n": False}
    # partial을 사용해 state를 콜백에 주입
    on_block = partial(_qc_on_block, state)
    walk_dict(data, on_block=on_block, required_keys=required_keys)
    return state["ok_bins"] and state["ok_n"]


# ─────────────────────────────────────────
# bins → (min,max) 변환
# ─────────────────────────────────────────


def bins_to_range(
    block: Dict[str, Any],
    qlow: float,
    qhigh: float,
    required_keys: set[str],
) -> Optional[Tuple[float, float]]:
    """
    단일 메트릭 블록의 bins 엣지들을 (qlow ~ qhigh) 분위 구간으로 변환해 (min, max) 튜플 반환
      - 길이 == 2면 그대로 (min, max)
      - 길이 > 2면 분위 인덱스에 맞춰 구간 추출
      - lo == hi 면 None
    """
    if not is_metric_block(block, required_keys):
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


def _adapt_on_block(
    out: Dict[str, Any],
    qlow: float,
    qhigh: float,
    required_keys: set[str],
    block: Dict[str, Any],
    path: Tuple[str, ...],
) -> None:
    """
    변환용 전역 콜백: 메트릭 블록을 {min,max}로 바꿔 out에 동일 경로로 써넣음.
     - 예: {"P2":{"elbow":{"min":..,"max":..}}, ...}
    """
    rng = bins_to_range(block, qlow, qhigh, required_keys)
    if not rng:
        return

    cur = out

    for key in path[:-1]:
        cur = cur.setdefault(key, {})
    cur[path[-1]] = {"min": rng[0], "max": rng[1]}


def adapt_bins_to_ranges(
    data: Dict[str, Any],
    *,
    qlow: float,
    qhigh: float,
    required_keys: set[str],
) -> Dict[str, Any]:
    """
    중첩 구조(phase/club/overall)를 그대로 따라가며,
    말단 메트릭 블록을 {min,max} 구조로 변환한 '동일한 트리 모양의 dict' 생성.
    """
    out: Dict[str, Any] = {}
    # partial로 out/파라미터 바인딩
    on_block = partial(_adapt_on_block, out, qlow, qhigh, required_keys)

    walk_dict(data, on_block=on_block, required_keys=required_keys)

    return out
