from __future__ import annotations

import pandas as pd


def risk_summary(df: pd.DataFrame) -> dict:
    outlier_count = int(df.get("rate_is_outlier", pd.Series(False, index=df.index)).sum()) if len(df) else 0
    avg_bid = df["bidder_count"].mean() if "bidder_count" in df.columns and not df.empty else None
    std = df["rate"].std() if "rate" in df.columns and not df.empty else None
    if avg_bid is None or avg_bid != avg_bid:
        comp = "판단불가"
    elif avg_bid >= 80:
        comp = "매우강"
    elif avg_bid >= 40:
        comp = "강"
    elif avg_bid >= 15:
        comp = "중"
    else:
        comp = "낮음"
    if std is None or std != std:
        risk = "판단불가"
    elif std >= 0.25:
        risk = "높음"
    elif std >= 0.12:
        risk = "중"
    else:
        risk = "낮음"
    return {"competition_level": comp, "risk_level": risk, "outlier_count": outlier_count, "avg_bidder_count": avg_bid, "std": std}
