from __future__ import annotations

import pandas as pd


def analyze_competitor(df: pd.DataFrame, min_count: int = 3) -> pd.DataFrame:
    winner_col = "winner_clean" if "winner_clean" in df.columns else "winner"
    if winner_col not in df.columns or "rate" not in df.columns:
        return pd.DataFrame()
    stats = (
        df.dropna(subset=[winner_col, "rate"])
        .groupby(winner_col)
        .agg(건수=("rate", "size"), 평균사정률=("rate", "mean"), 최저사정률=("rate", "min"), 최고사정률=("rate", "max"))
        .reset_index()
        .rename(columns={winner_col: "winner"})
    )
    stats = stats[stats["건수"] >= min_count].copy()
    return stats.sort_values(["건수", "평균사정률"], ascending=[False, True]).round(4)


def competitor_by_agency(df: pd.DataFrame, competitor: str) -> pd.DataFrame:
    winner_col = "winner_clean" if "winner_clean" in df.columns else "winner"
    agency_col = "agency_clean" if "agency_clean" in df.columns else "agency"
    if winner_col not in df.columns or agency_col not in df.columns or "rate" not in df.columns:
        return pd.DataFrame()
    sub = df[df[winner_col] == competitor]
    if sub.empty:
        return pd.DataFrame()
    return (
        sub.groupby(agency_col)
        .agg(건수=("rate", "size"), 평균사정률=("rate", "mean"))
        .reset_index()
        .rename(columns={agency_col: "agency"})
        .sort_values("건수", ascending=False)
        .round(4)
    )
