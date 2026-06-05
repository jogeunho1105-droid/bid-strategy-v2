from __future__ import annotations

import pandas as pd


def overview(df: pd.DataFrame) -> dict[str, float | int]:
    rate = df["rate"] if "rate" in df.columns else pd.Series(dtype=float)
    return {
        "total_count": int(len(df)),
        "avg_rate": float(rate.mean()) if rate.notna().any() else float("nan"),
        "median_rate": float(rate.median()) if rate.notna().any() else float("nan"),
        "min_rate": float(rate.min()) if rate.notna().any() else float("nan"),
        "max_rate": float(rate.max()) if rate.notna().any() else float("nan"),
    }


def monthly_trend(df: pd.DataFrame) -> pd.DataFrame:
    if "open_date" not in df.columns or "rate" not in df.columns:
        return pd.DataFrame()
    data = df[df["open_date"].notna() & df["rate"].notna()].copy()
    if data.empty:
        return pd.DataFrame()
    data["월"] = data["open_date"].dt.to_period("M").astype(str)
    return (
        data.groupby("월", as_index=False)
        .agg(평균사정률=("rate", "mean"), 중앙사정률=("rate", "median"), 건수=("rate", "size"))
        .round({"평균사정률": 4, "중앙사정률": 4})
    )


def group_rate_stats(df: pd.DataFrame, group_col: str, min_count: int = 3) -> pd.DataFrame:
    if group_col not in df.columns or "rate" not in df.columns:
        return pd.DataFrame()
    stats = (
        df.dropna(subset=[group_col, "rate"])
        .groupby(group_col)
        .agg(건수=("rate", "size"), 평균사정률=("rate", "mean"), 중앙사정률=("rate", "median"), 표준편차=("rate", "std"))
        .reset_index()
        .rename(columns={group_col: "구분"})
    )
    stats = stats[stats["건수"] >= min_count].copy()
    if stats.empty:
        return stats
    return stats.sort_values(["건수", "평균사정률"], ascending=[False, True]).round(4)
