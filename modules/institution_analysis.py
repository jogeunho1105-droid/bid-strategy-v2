from __future__ import annotations

import numpy as np
import pandas as pd


def _level_by_volatility(std: float) -> str:
    if pd.isna(std): return "판단불가"
    if std < 0.12: return "낮음"
    if std < 0.25: return "보통"
    return "높음"


def _competition_level(avg_bidder_count: float) -> str:
    if pd.isna(avg_bidder_count): return "판단불가"
    if avg_bidder_count >= 80: return "매우강"
    if avg_bidder_count >= 40: return "강"
    if avg_bidder_count >= 15: return "보통"
    return "약"


def _risk_level(std: float, recent_drop: float, avg_bidder_count: float) -> str:
    score = 0
    if not pd.isna(std):
        score += 2 if std >= 0.25 else 1 if std >= 0.12 else 0
    if not pd.isna(recent_drop):
        score += 2 if recent_drop <= -0.20 else 1 if recent_drop <= -0.10 else 0
    if not pd.isna(avg_bidder_count):
        score += 2 if avg_bidder_count >= 80 else 1 if avg_bidder_count >= 40 else 0
    if score >= 5: return "높음"
    if score >= 3: return "중"
    return "낮음"


def analyze_agency(df: pd.DataFrame, min_count: int = 5) -> pd.DataFrame:
    if "rate" not in df.columns:
        return pd.DataFrame()
    agency_col = "agency_clean" if "agency_clean" in df.columns else "agency"
    if agency_col not in df.columns:
        return pd.DataFrame()
    data = df.copy()
    if "open_date" in data.columns:
        data = data.sort_values("open_date")
    rows = []
    for agency, g in data.groupby(agency_col):
        g = g[g["rate"].notna()].copy()
        if len(g) < min_count:
            continue
        recent = g.tail(20)
        avg = g["rate"].mean()
        recent_avg = recent["rate"].mean()
        std = g["rate"].std()
        avg_bidders = g["bidder_count"].mean() if "bidder_count" in g.columns else np.nan
        rows.append({
            "agency": agency,
            "건수": len(g),
            "평균사정률": round(avg, 4),
            "중앙사정률": round(g["rate"].median(), 4),
            "최근20건평균": round(recent_avg, 4),
            "최근차이": round(recent_avg - avg, 4),
            "표준편차": round(std, 4) if not pd.isna(std) else np.nan,
            "변동성": _level_by_volatility(std),
            "평균업체수": round(avg_bidders, 1) if not pd.isna(avg_bidders) else np.nan,
            "경쟁강도": _competition_level(avg_bidders),
            "위험도": _risk_level(std, recent_avg - avg, avg_bidders),
        })
    out = pd.DataFrame(rows)
    if out.empty:
        return out
    return out.sort_values(["위험도", "경쟁강도", "건수"], ascending=[False, False, False]).reset_index(drop=True)


def agency_strategy_comment(row: pd.Series) -> str:
    comments = []
    risk = row.get("위험도", "판단불가")
    competition = row.get("경쟁강도", "판단불가")
    recent_gap = row.get("최근차이", np.nan)
    if risk == "높음": comments.append("최근 변동성 또는 경쟁 강도가 높아 공격형 투찰은 주의가 필요합니다.")
    elif risk == "중": comments.append("중간 수준의 리스크가 있어 최근 흐름을 반영한 중립 전략이 적합합니다.")
    else: comments.append("상대적으로 안정적인 기관 패턴으로 판단됩니다.")
    if not pd.isna(recent_gap):
        if recent_gap < -0.1: comments.append("최근 20건 평균이 전체 평균보다 낮아지는 흐름입니다.")
        elif recent_gap > 0.1: comments.append("최근 20건 평균이 전체 평균보다 높아지는 흐름입니다.")
        else: comments.append("최근 흐름은 전체 평균과 큰 차이가 없습니다.")
    if competition in ["강", "매우강"]:
        comments.append("업체수 기준 경쟁 강도가 높으므로 정교한 구간 설정이 필요합니다.")
    return " ".join(comments)
