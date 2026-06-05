from __future__ import annotations

import pandas as pd


def _filtered(df: pd.DataFrame, agency: str | None = None, category: str | None = None) -> pd.DataFrame:
    out = df.copy()
    if agency and "agency_clean" in out.columns:
        out = out[out["agency_clean"] == agency]
    elif agency and "agency" in out.columns:
        out = out[out["agency"] == agency]
    if category and "category_clean" in out.columns:
        out = out[out["category_clean"] == category]
    elif category and "category" in out.columns:
        out = out[out["category"] == category]
    return out


def recommend_rate(df: pd.DataFrame, agency: str | None = None, category: str | None = None) -> dict[str, object]:
    sub = _filtered(df, agency=agency, category=category)
    if "rate" not in sub.columns or sub["rate"].dropna().shape[0] < 5:
        return {"status": "데이터부족", "sample_count": int(sub.shape[0])}

    rate = sub["rate"].dropna()
    mean = float(rate.mean())
    median = float(rate.median())
    std = float(rate.std()) if len(rate) >= 2 else 0.0
    recent = rate.tail(min(20, len(rate)))
    recent_mean = float(recent.mean())
    neutral = 0.55 * mean + 0.25 * recent_mean + 0.20 * median
    stable = neutral - 0.4 * std
    aggressive = neutral + 0.4 * std
    density = float(((rate >= neutral - 0.2) & (rate <= neutral + 0.2)).mean())
    heat_score = round((std * 10) + (1 - density) * 5, 2)
    difficulty = "높음" if heat_score >= 8 else "보통" if heat_score >= 5 else "낮음"

    return {
        "status": "산출완료",
        "sample_count": int(len(rate)),
        "stable": round(stable, 4),
        "neutral": round(neutral, 4),
        "aggressive": round(aggressive, 4),
        "density": density,
        "heat_score": heat_score,
        "difficulty": difficulty,
        "volatility": round(std, 4),
        "comment": f"평균 {mean:+.4f}%, 최근 {len(recent)}건 평균 {recent_mean:+.4f}%를 반영했습니다.",
    }
