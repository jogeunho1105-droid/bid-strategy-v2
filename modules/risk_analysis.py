from __future__ import annotations

import pandas as pd


def competition_level(avg_bidder_count: float | None) -> str:
    if avg_bidder_count is None or pd.isna(avg_bidder_count):
        return "판단불가"
    if avg_bidder_count >= 80:
        return "강"
    if avg_bidder_count >= 30:
        return "중"
    return "약"


def risk_summary(df: pd.DataFrame) -> dict:
    rate_std = float(df["rate"].std()) if "rate" in df.columns and df["rate"].notna().any() else None
    avg_bidders = float(df["bidder_count"].mean()) if "bidder_count" in df.columns and df["bidder_count"].notna().any() else None
    outlier_count = int(df["rate_is_outlier"].sum()) if "rate_is_outlier" in df.columns else 0

    risk = "낮음"
    if rate_std and rate_std >= 0.35:
        risk = "높음"
    elif rate_std and rate_std >= 0.18:
        risk = "중간"

    return {
        "rate_volatility": rate_std,
        "avg_bidder_count": avg_bidders,
        "competition_level": competition_level(avg_bidders),
        "outlier_count": outlier_count,
        "risk_level": risk,
    }
