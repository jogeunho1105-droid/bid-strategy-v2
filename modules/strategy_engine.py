from __future__ import annotations

import numpy as np
import pandas as pd


def weighted_recent_rate(df: pd.DataFrame, n: int = 30) -> float | None:
    if "rate" not in df.columns:
        return None
    temp = df.dropna(subset=["rate"]).copy()
    if "open_date" in temp.columns:
        temp = temp.sort_values("open_date", ascending=False)
    temp = temp.head(n)
    if temp.empty:
        return None
    weights = np.linspace(1.0, 0.35, len(temp))
    return float(np.average(temp["rate"], weights=weights))


def recommend_rate(df: pd.DataFrame, agency: str | None = None, category: str | None = None) -> dict:
    temp = df.copy()
    if agency and "agency" in temp.columns:
        agency_df = temp[temp["agency"] == agency]
        if len(agency_df) >= 5:
            temp = agency_df
    if category and "category" in temp.columns:
        category_df = temp[temp["category"] == category]
        if len(category_df) >= 5:
            temp = category_df

    base = weighted_recent_rate(temp, n=30)
    if base is None:
        return {"status": "데이터 부족", "base": None, "stable": None, "neutral": None, "aggressive": None}

    std = float(temp["rate"].dropna().tail(50).std()) if "rate" in temp.columns else 0.0
    adj = min(max(std * 0.25, 0.015), 0.08) if not np.isnan(std) else 0.03

    return {
        "status": "산출완료",
        "base": base,
        "stable": base + adj,
        "neutral": base,
        "aggressive": base - adj,
        "volatility": std,
        "sample_count": int(temp["rate"].notna().sum()),
    }
