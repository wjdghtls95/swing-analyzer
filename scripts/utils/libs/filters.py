from typing import Dict, Any, Optional
from datetime import datetime, timezone


def row_passes_filters(
    row: Dict[str, Any],
    *,
    club: Optional[str] = None,
    phase_method: Optional[str] = None,
    since: Optional[datetime] = None,
    until: Optional[datetime] = None,
) -> bool:
    if club and str(row.get("input.club")) != club:
        return False
    if phase_method and str(row.get("phase.method")) != phase_method:
        return False

    ts = row.get("timestamp")
    if ts is not None and (since or until):
        try:
            dt = datetime.fromtimestamp(int(ts), tz=timezone.utc)
            if since and dt < since:
                return False
            if until and dt >= until:
                return False
        except Exception:
            pass
    return True
