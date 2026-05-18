from __future__ import annotations

import pandas as pd

from modules.basic_analysis import group_rate_stats


def analyze_agency(df: pd.DataFrame, min_count: int = 5) -> pd.DataFrame:
    return group_rate_stats(df, "agency", min_count=min_count)
