from __future__ import annotations

import pandas as pd


def risk_summary(df: pd.DataFrame) -> dict[str, object]:
    if df.empty or "rate" not in df.columns:
        return {
            "competition_level": "판단불가",
            "risk_level": "데이터 부족",
            "sample_count": 0,
            "volatility": None,
            "comment": "분석 가능한 사정률 데이터가 부족합니다.",
        }

    rate = df["rate"].dropna()
    std = float(rate.std()) if len(rate) >= 2 else 0.0
    bidder_mean = float(df["bidder_count"].mean()) if "bidder_count" in df.columns and df["bidder_count"].notna().any() else None

    if bidder_mean is None:
        competition_level = "보통"
    elif bidder_mean >= 80:
        competition_level = "높음"
    elif bidder_mean >= 25:
        competition_level = "보통"
    else:
        competition_level = "낮음"

    if std >= 0.65:
        risk_level = "높음"
    elif std >= 0.4:
        risk_level = "보통"
    else:
        risk_level = "낮음"

    return {
        "competition_level": competition_level,
        "risk_level": risk_level,
        "sample_count": int(len(rate)),
        "avg_rate": round(float(rate.mean()), 4),
        "median_rate": round(float(rate.median()), 4),
        "volatility": round(std, 4),
        "bidder_mean": round(bidder_mean, 1) if bidder_mean is not None else None,
        "comment": f"표본 {len(rate):,}건 기준 변동성 {std:.4f}%입니다.",
    }
