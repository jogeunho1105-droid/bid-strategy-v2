from __future__ import annotations

import pandas as pd


def overview(df: pd.DataFrame) -> dict:
    return {
        "total_count": len(df),
        "valid_rate_count": int(df["rate"].notna().sum()) if "rate" in df.columns else 0,
        "agency_count": int(df["agency"].nunique()) if "agency" in df.columns else 0,
        "winner_count": int(df["winner"].nunique()) if "winner" in df.columns else 0,
        "avg_rate": float(df["rate"].mean()) if "rate" in df.columns else None,
        "median_rate": float(df["rate"].median()) if "rate" in df.columns else None,
    }


def group_rate_stats(df: pd.DataFrame, group_col: str, min_count: int = 3) -> pd.DataFrame:
    if group_col not in df.columns or "rate" not in df.columns:
        return pd.DataFrame()
    result = (
        df.groupby(group_col)
        .agg(
            건수=("rate", "count"),
            평균사정률=("rate", "mean"),
            중앙값=("rate", "median"),
            표준편차=("rate", "std"),
            최저=("rate", "min"),
            최고=("rate", "max"),
        )
        .reset_index()
    )
    result = result[result["건수"] >= min_count]
    return result.sort_values(["건수", "평균사정률"], ascending=[False, True])


def monthly_trend(df: pd.DataFrame) -> pd.DataFrame:
    if "open_date" not in df.columns or "rate" not in df.columns:
        return pd.DataFrame()
    temp = df.dropna(subset=["open_date", "rate"]).copy()
    temp["월"] = temp["open_date"].dt.to_period("M").astype(str)
    return temp.groupby("월").agg(건수=("rate", "count"), 평균사정률=("rate", "mean")).reset_index()
