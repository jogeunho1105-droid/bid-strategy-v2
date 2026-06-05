from __future__ import annotations

import pandas as pd


def market_status(df: pd.DataFrame, n: int = 30) -> dict[str, object]:
    if df.empty or "rate" not in df.columns:
        return {
            "market_status": "판단불가",
            "trend": {"direction": "판단불가"},
            "volatility": {"volatility_status": "판단불가"},
            "bidder": {"bidder_status": "판단불가"},
            "comment": "분석 가능한 데이터가 없습니다.",
        }

    data = df.copy()
    if "open_date" in data.columns:
        data = data.sort_values("open_date")
    recent = data.tail(n)
    rate = recent["rate"].dropna()
    if rate.empty:
        return {
            "market_status": "판단불가",
            "trend": {"direction": "판단불가"},
            "volatility": {"volatility_status": "판단불가"},
            "bidder": {"bidder_status": "판단불가"},
            "comment": "최근 구간에 사정률 데이터가 없습니다.",
        }

    first = float(rate.head(max(1, len(rate) // 3)).mean())
    last = float(rate.tail(max(1, len(rate) // 3)).mean())
    drift = last - first
    direction = "상승" if drift > 0.05 else "하락" if drift < -0.05 else "보합"
    std = float(rate.std()) if len(rate) >= 2 else 0.0
    vol_status = "높음" if std >= 0.65 else "보통" if std >= 0.4 else "낮음"

    bidder_status = "판단불가"
    bidder_mean = None
    if "bidder_count" in recent.columns and recent["bidder_count"].notna().any():
        bidder_mean = float(recent["bidder_count"].mean())
        bidder_status = "과열" if bidder_mean >= 80 else "보통" if bidder_mean >= 25 else "한산"

    market = "공격주의" if vol_status == "높음" or bidder_status == "과열" else "중립" if direction == "보합" else direction
    return {
        "market_status": market,
        "trend": {"direction": direction, "drift": round(drift, 4), "recent_mean": round(last, 4)},
        "volatility": {"volatility_status": vol_status, "std": round(std, 4)},
        "bidder": {"bidder_status": bidder_status, "avg_bidders": round(bidder_mean, 1) if bidder_mean is not None else None},
        "comment": f"최근 {len(rate):,}건 기준 방향은 {direction}, 변동성은 {vol_status}입니다.",
    }
