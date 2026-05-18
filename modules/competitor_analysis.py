from __future__ import annotations

import pandas as pd


def analyze_competitor(df: pd.DataFrame, min_count: int = 3) -> pd.DataFrame:
    col = "winner_clean" if "winner_clean" in df.columns else "winner"
    if col not in df.columns or "rate" not in df.columns:
        return pd.DataFrame()
    out = df.dropna(subset=[col, "rate"]).groupby(col)["rate"].agg(["count", "mean", "median", "std"]).reset_index()
    out = out[out["count"] >= min_count]
    if out.empty:
        return out
    out.columns = ["winner", "건수", "평균사정률", "중앙사정률", "표준편차"]
    return out.sort_values("건수", ascending=False)


def competitor_by_agency(df: pd.DataFrame, competitor: str) -> pd.DataFrame:
    wcol = "winner_clean" if "winner_clean" in df.columns else "winner"
    acol = "agency_clean" if "agency_clean" in df.columns else "agency"
    if wcol not in df.columns or acol not in df.columns or "rate" not in df.columns:
        return pd.DataFrame()
    temp = df[df[wcol] == competitor]
    out = temp.groupby(acol)["rate"].agg(["count", "mean", "median", "std"]).reset_index()
    out.columns = ["agency", "건수", "평균사정률", "중앙사정률", "표준편차"]
    return out.sort_values("건수", ascending=False)
