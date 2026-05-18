from __future__ import annotations

import numpy as np
import pandas as pd


def _level_by_volatility(std: float) -> str:
    if pd.isna(std):
        return "판단불가"
    if std < 0.12:
        return "낮음"
    if std < 0.25:
        return "보통"
    return "높음"


def _competition_level(avg_bidder_count: float) -> str:
    if pd.isna(avg_bidder_count):
        return "판단불가"
    if avg_bidder_count >= 80:
        return "매우강"
    if avg_bidder_count >= 40:
        return "강"
    if avg_bidder_count >= 15:
        return "보통"
    return "약"


def _risk_level(std: float, recent_drop: float, avg_bidder_count: float) -> str:
    score = 0

    if not pd.isna(std):
        if std >= 0.25:
            score += 2
        elif std >= 0.12:
            score += 1

    if not pd.isna(recent_drop):
        if recent_drop <= -0.20:
            score += 2
        elif recent_drop <= -0.10:
            score += 1

    if not pd.isna(avg_bidder_count):
        if avg_bidder_count >= 80:
            score += 2
        elif avg_bidder_count >= 40:
            score += 1

    if score >= 5:
        return "높음"
    if score >= 3:
        return "중"
    return "낮음"


def analyze_agency(df: pd.DataFrame, min_count: int = 5) -> pd.DataFrame:
    """
    기관별 사정률 패턴 분석.
    - 전체 평균
    - 최근 20건 평균
    - 변동성
    - 업체수 기반 경쟁강도
    - 최근 하락폭 기반 위험도
    """

    if "agency" not in df.columns or "rate" not in df.columns:
        return pd.DataFrame()

    data = df.copy()

    agency_col = "agency_clean" if "agency_clean" in data.columns else "agency"

    if "open_date" in data.columns:
        data = data.sort_values("open_date")
    else:
        data = data.reset_index(drop=True)

    rows = []

    for agency, g in data.groupby(agency_col):
        g = g[g["rate"].notna()].copy()

        if len(g) < min_count:
            continue

        recent = g.tail(20)

        avg_rate = g["rate"].mean()
        median_rate = g["rate"].median()
        recent_avg_rate = recent["rate"].mean()
        std_rate = g["rate"].std()

        recent_gap = recent_avg_rate - avg_rate

        if "bidder_count" in g.columns:
            avg_bidder_count = g["bidder_count"].mean()
        else:
            avg_bidder_count = np.nan

        rows.append(
            {
                "agency": agency,
                "건수": len(g),
                "평균사정률": round(avg_rate, 4),
                "중앙사정률": round(median_rate, 4),
                "최근20건평균": round(recent_avg_rate, 4),
                "최근차이": round(recent_gap, 4),
                "표준편차": round(std_rate, 4) if not pd.isna(std_rate) else np.nan,
                "변동성": _level_by_volatility(std_rate),
                "평균업체수": round(avg_bidder_count, 1) if not pd.isna(avg_bidder_count) else np.nan,
                "경쟁강도": _competition_level(avg_bidder_count),
                "위험도": _risk_level(std_rate, recent_gap, avg_bidder_count),
            }
        )

    result = pd.DataFrame(rows)

    if result.empty:
        return result

    return result.sort_values(
        by=["위험도", "경쟁강도", "건수"],
        ascending=[False, False, False],
    ).reset_index(drop=True)


def agency_strategy_comment(row: pd.Series) -> str:
    """
    기관별 전략 코멘트 생성.
    Streamlit 상세 분석 카드에 사용.
    """

    risk = row.get("위험도", "판단불가")
    competition = row.get("경쟁강도", "판단불가")
    recent_gap = row.get("최근차이", np.nan)

    comments = []

    if risk == "높음":
        comments.append("최근 변동성 또는 경쟁 강도가 높아 공격형 투찰은 주의가 필요합니다.")
    elif risk == "중":
        comments.append("중간 수준의 리스크가 있어 최근 흐름을 반영한 중립 전략이 적합합니다.")
    else:
        comments.append("상대적으로 안정적인 기관 패턴으로 판단됩니다.")

    if not pd.isna(recent_gap):
        if recent_gap < -0.1:
            comments.append("최근 20건 평균이 전체 평균보다 낮아지는 흐름입니다.")
        elif recent_gap > 0.1:
            comments.append("최근 20건 평균이 전체 평균보다 높아지는 흐름입니다.")
        else:
            comments.append("최근 흐름은 전체 평균과 큰 차이가 없습니다.")

    if competition in ["강", "매우강"]:
        comments.append("업체수 기준 경쟁 강도가 높으므로 보수적 판단보다 정교한 구간 설정이 필요합니다.")

    return " ".join(comments)
