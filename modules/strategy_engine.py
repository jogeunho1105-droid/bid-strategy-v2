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


def density_score(df: pd.DataFrame, center: float, band: float = 0.03, n: int = 50) -> float:
    """
    최근 n건 중 중심값 ± band 안에 들어오는 비율.
    값이 높을수록 평균 근처로 시장이 몰린다는 의미.
    """
    if "rate" not in df.columns or center is None:
        return np.nan

    temp = df.dropna(subset=["rate"]).copy()

    if "open_date" in temp.columns:
        temp = temp.sort_values("open_date", ascending=False)

    temp = temp.head(n)

    if temp.empty:
        return np.nan

    within = temp["rate"].between(center - band, center + band)
    return float(within.mean())


def avg_bidder_count(df: pd.DataFrame, n: int = 50) -> float:
    if "bidder_count" not in df.columns:
        return np.nan

    temp = df.dropna(subset=["bidder_count"]).copy()

    if "open_date" in temp.columns:
        temp = temp.sort_values("open_date", ascending=False)

    temp = temp.head(n)

    if temp.empty:
        return np.nan

    return float(temp["bidder_count"].mean())


def market_heat_score(density: float, avg_bidders: float) -> float:
    """
    과열지수.
    단순 공식:
    - 밀집도 0~1
    - 평균 업체수
    를 결합해 0~100 점수로 환산.
    """
    if pd.isna(density) or pd.isna(avg_bidders):
        return np.nan

    bidder_factor = min(avg_bidders / 100, 1.5)
    score = density * bidder_factor * 100
    return round(float(score), 2)


def difficulty_level(heat_score: float, density: float, avg_bidders: float) -> str:
    if pd.isna(heat_score):
        return "판단불가"

    if heat_score >= 70:
        return "매우어려움"
    if heat_score >= 45:
        return "어려움"
    if heat_score >= 25:
        return "보통"
    return "낮음"


def strategy_comment(rec: dict) -> str:
    difficulty = rec.get("difficulty", "판단불가")
    density = rec.get("density", np.nan)
    avg_bidders = rec.get("avg_bidders", np.nan)

    comments = []

    if difficulty == "매우어려움":
        comments.append("평균 근처 밀집도가 높고 참여업체 수가 많아 실질 낙찰 난이도가 매우 높습니다.")
        comments.append("단순 평균 추종보다는 기관 최근 흐름과 세부 구간 분산 전략이 필요합니다.")
    elif difficulty == "어려움":
        comments.append("시장 참여자가 평균 구간에 비교적 많이 몰리는 구간입니다.")
        comments.append("중립형 중심 접근이 가능하나, 공격형 투찰은 신중해야 합니다.")
    elif difficulty == "보통":
        comments.append("경쟁 난이도는 보통 수준입니다.")
        comments.append("최근 흐름과 변동성을 함께 반영한 중립 전략이 적합합니다.")
    elif difficulty == "낮음":
        comments.append("밀집도와 업체수 기준으로는 과열 부담이 상대적으로 낮습니다.")
        comments.append("기관 성향이 안정적이면 공격형 구간도 일부 검토 가능합니다.")
    else:
        comments.append("난이도 판단을 위한 데이터가 부족합니다.")

    if not pd.isna(density):
        comments.append(f"최근 밀집도는 {density:.1%} 수준입니다.")

    if not pd.isna(avg_bidders):
        comments.append(f"최근 평균 업체수는 약 {avg_bidders:.1f}개입니다.")

    return " ".join(comments)


def recommend_rate(df: pd.DataFrame, agency: str | None = None, category: str | None = None) -> dict:
    temp = df.copy()

    agency_col = "agency_clean" if "agency_clean" in temp.columns else "agency"
    category_col = "category_clean" if "category_clean" in temp.columns else "category"

    if agency and agency_col in temp.columns:
        agency_df = temp[temp[agency_col] == agency]
        if len(agency_df) >= 5:
            temp = agency_df

    if category and category_col in temp.columns:
        category_df = temp[temp[category_col] == category]
        if len(category_df) >= 5:
            temp = category_df

    base = weighted_recent_rate(temp, n=30)

    if base is None:
        return {
            "status": "데이터 부족",
            "base": None,
            "stable": None,
            "neutral": None,
            "aggressive": None,
        }

    recent_rates = temp["rate"].dropna().tail(50)
    std = float(recent_rates.std()) if len(recent_rates) >= 2 else 0.0

    density = density_score(temp, center=base, band=0.03, n=50)
    bidders = avg_bidder_count(temp, n=50)
    heat = market_heat_score(density, bidders)
    difficulty = difficulty_level(heat, density, bidders)

    base_adj = min(max(std * 0.25, 0.015), 0.08) if not np.isnan(std) else 0.03

    # 과열 시장에서는 공격형/안정형 폭을 과도하게 벌리지 않음
    if difficulty == "매우어려움":
        adj = min(base_adj, 0.03)
    elif difficulty == "어려움":
        adj = min(base_adj, 0.05)
    else:
        adj = base_adj

    rec = {
        "status": "산출완료",
        "base": base,
        "stable": base + adj,
        "neutral": base,
        "aggressive": base - adj,
        "volatility": std,
        "density": density,
        "avg_bidders": bidders,
        "heat_score": heat,
        "difficulty": difficulty,
        "sample_count": int(temp["rate"].notna().sum()),
        "adjust_width": adj,
    }

    rec["comment"] = strategy_comment(rec)
    return rec
