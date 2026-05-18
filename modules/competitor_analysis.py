from __future__ import annotations

import pandas as pd

from modules.basic_analysis import group_rate_stats


def analyze_competitor(df: pd.DataFrame, min_count: int = 3) -> pd.DataFrame:
    return group_rate_stats(df, "winner", min_count=min_count)


def competitor_by_agency(df: pd.DataFrame, competitor: str) -> pd.DataFrame:
    if "winner" not in df.columns or "agency" not in df.columns or "rate" not in df.columns:
        return pd.DataFrame()
    temp = df[df["winner"] == competitor].copy()
    return (
        temp.groupby("agency")
        .agg(건수=("rate", "count"), 평균사정률=("rate", "mean"), 최저=("rate", "min"), 최고=("rate", "max"))
        .reset_index()
        .sort_values("건수", ascending=False)
    )
