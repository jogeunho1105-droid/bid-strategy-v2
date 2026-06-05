from __future__ import annotations

import math


def fmt_num(value) -> str:
    try:
        if value is None or (isinstance(value, float) and math.isnan(value)):
            return "-"
        return f"{int(value):,}"
    except Exception:
        return "-"


def fmt_pct(value) -> str:
    try:
        if value is None or (isinstance(value, float) and math.isnan(value)):
            return "-"
        return f"{float(value):+.4f}%"
    except Exception:
        return "-"
