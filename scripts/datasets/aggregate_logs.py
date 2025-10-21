#!/usr/bin/env python3
import glob, os
from pathlib import Path
from datetime import datetime, timezone
import pandas as pd

from libs.jsonio import load_json
from libs.flatten import (
    flatten_core_blocks,
    flatten_phase_metrics,
    flatten_diag_by_phase,
)
from libs.filters import row_passes_filters
from libs.stats import summarize_counts
from libs.cli_utils import parse_args, ensure_parent_dir


def main():
    args = parse_args()

    # 날짜 인자 파싱
    def _parse_date(s):
        return datetime.fromisoformat(s).replace(tzinfo=timezone.utc) if s else None

    since = _parse_date(args.since)
    until = _parse_date(args.until)

    files = sorted(glob.glob(args.glob))
    if not files:
        print(f"[aggregate] no files matched: {args.glob}")
        return

    rows = []
    for p in files:
        try:
            d = load_json(p)
            row = flatten_core_blocks(d)
            row["file"] = os.path.basename(p)
            row.update(flatten_phase_metrics(d.get("phase_metrics")))
            row.update(flatten_diag_by_phase(d.get("diagnosis_by_phase")))
            if row_passes_filters(
                row,
                club=args.club,
                phase_method=args.phase_method,
                since=since,
                until=until,
            ):
                rows.append(row)
        except Exception as e:
            print(f"[aggregate] skip {p}: {e}")

    if not rows:
        print("[aggregate] no rows after filtering")
        return

    df = pd.DataFrame(rows)
    out_csv = Path(args.out)
    ensure_parent_dir(out_csv)
    df.to_csv(out_csv, index=False)

    try:
        df.to_parquet(out_csv.with_suffix(".parquet"), index=False)
    except Exception:
        pass

    summary = summarize_counts(df, ["input.club", "env", "phase.method"])
    print(f"[aggregate] rows={len(df)}")
    for k, v in summary.items():
        print(f"[aggregate] by_{k}={v}")
    print(f"[aggregate] saved csv: {out_csv}")


if __name__ == "__main__":
    main()
