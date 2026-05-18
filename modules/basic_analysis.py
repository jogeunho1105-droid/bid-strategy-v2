from __future__ import annotations

import pandas as pd


def overview(df: pd.DataFrame) -> dict:
    if "rate" not in df.columns or df.empty:
        return {"total_count": len(df), "avg_rate": None, "median_rate": None}
    return {
        "total_count": len(df),
        "avg_rate": df["rate"].mean(),
        "median_rate": df["rate"].median(),
    }


def group_rate_stats(df: pd.DataFrame, group_col: str, min_count: int = 3) -> pd.DataFrame:
    if group_col not in df.columns or "rate" not in df.columns:
        return pd.DataFrame()
    g = df.dropna(subset=[group_col, "rate"]).groupby(group_col)["rate"].agg(["count", "mean", "median", "std"])
    g = g[g["count"] >= min_count].reset_index()
    if g.empty:
        return g
    g.columns = [group_col, "건수", "평균사정률", "중앙사정률", "표준편차"]
    return g.sort_values("건수", ascending=False)


def monthly_trend(df: pd.DataFrame) -> pd.DataFrame:
    if "open_date" not in df.columns or "rate" not in df.columns:
        return pd.DataFrame()
    temp = df.dropna(subset=["open_date", "rate"]).copy()
    if temp.empty:
        return pd.DataFrame()
    temp["월"] = temp["open_date"].dt.to_period("M").astype(str)
    out = temp.groupby("월")["rate"].agg(["count", "mean", "median", "std"]).reset_index()
    out.columns = ["월", "건수", "평균사정률", "중앙사정률", "표준편차"]
    return out
