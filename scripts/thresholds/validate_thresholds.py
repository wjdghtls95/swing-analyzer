from __future__ import annotations
import json, sys
from pathlib import Path
from typing import Dict, Any, List

REQUIRED_MSG_KEYS = {"bins", "mean", "std", "n"}


def _is_num(x):
    return isinstance(x, (int, float)) and x == x


def _validate_metric_block(name: str, block: Dict[str, Any], errors: List[str]):
    missing = REQUIRED_MSG_KEYS - set(block.keys())
    if missing:
        errors.append(f"[{name}] missing keys: {sorted(missing)}")
        return
    bins = block["bins"]
    if not isinstance(bins, list) or len(bins) < 2:
        errors.append(f"[{name}] bins must be list(len>=2)")
    else:
        # 오름차순 검사
        for i in range(1, len(bins)):
            if not (_is_num(bins[i - 1]) and _is_num(bins[i])) or bins[i] < bins[i - 1]:
                errors.append(
                    f"[{name}] bins not nondecreasing at idx {i}: {bins[i - 1]} -> {bins[i]}"
                )
                break
    if not all(_is_num(block[k]) for k in ("mean", "std")):
        errors.append(f"[{name}] mean/std must be numbers")
    if not isinstance(block["n"], int) or block["n"] < 0:
        errors.append(f"[{name}] n must be non-negative int")


def _walk(d: Dict[str, Any], prefix: str, errors: List[str]):
    # phase/club/overall 어떤 형태든, 말단이 metric block(dict with bins/mean/std/n)
    for k, v in d.items():
        name = f"{prefix}.{k}" if prefix else k
        if isinstance(v, dict) and set(REQUIRED_MSG_KEYS).issubset(v.keys()):
            _validate_metric_block(name, v, errors)
        elif isinstance(v, dict):
            _walk(v, name, errors)
        else:
            # 허용: 값이 dict가 아니면 무시(phase 없거나 빈 값일 수 있음)
            pass


def main():
    if len(sys.argv) < 2:
        print(
            "Usage: python -m scripts.thresholds.validate_thresholds <path/to/thresholds.json>"
        )
        sys.exit(2)
    path = Path(sys.argv[1])
    if not path.exists():
        print(f"File not found: {path}")
        sys.exit(2)
    data = json.loads(path.read_text(encoding="utf-8"))
    errors: List[str] = []
    _walk(data, "", errors)
    if errors:
        print("❌ Thresholds validation failed:")
        for e in errors:
            print(" -", e)
        sys.exit(1)
    print("✅ Thresholds validation OK:", path)


if __name__ == "__main__":
    main()
