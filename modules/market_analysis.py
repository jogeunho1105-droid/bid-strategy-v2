from __future__ import annotations

import numpy as np
import pandas as pd


def _recent_old_split(df: pd.DataFrame, n: int = 30):
    if "rate" not in df.columns:
        return None, None
    temp = df.dropna(subset=["rate"]).copy()
    if "open_date" in temp.columns:
        temp = temp.sort_values("open_date")
    if len(temp) < n * 2:
        return None, None
    return temp.iloc[-n*2:-n], temp.iloc[-n:]


def trend_direction(df: pd.DataFrame, n: int = 30) -> dict:
    old, recent = _recent_old_split(df, n)
    if old is None:
        return {"status":"데이터 부족", "direction":"판단불가", "gap":np.nan}
    old_avg, recent_avg = old["rate"].mean(), recent["rate"].mean()
    gap = recent_avg - old_avg
    direction = "저가화 진행" if gap <= -0.10 else "보수화 진행" if gap >= 0.10 else "횡보"
    return {"status":"산출완료", "direction":direction, "old_avg":old_avg, "recent_avg":recent_avg, "gap":gap}


def volatility_change(df: pd.DataFrame, n: int = 30) -> dict:
    old, recent = _recent_old_split(df, n)
    if old is None:
        return {"status":"데이터 부족", "volatility_status":"판단불가", "gap":np.nan}
    old_std, recent_std = old["rate"].std(), recent["rate"].std()
    gap = recent_std - old_std
    status = "변동 확대" if gap >= 0.08 else "안정화" if gap <= -0.08 else "유사"
    return {"status":"산출완료", "volatility_status":status, "old_std":old_std, "recent_std":recent_std, "gap":gap}


def bidder_trend(df: pd.DataFrame, n: int = 30) -> dict:
    if "bidder_count" not in df.columns:
        return {"status":"업체수 없음", "bidder_status":"판단불가", "gap":np.nan}
    temp = df.dropna(subset=["bidder_count"]).copy()
    if "open_date" in temp.columns:
        temp = temp.sort_values("open_date")
    if len(temp) < n * 2:
        return {"status":"데이터 부족", "bidder_status":"판단불가", "gap":np.nan}
    old, recent = temp.iloc[-n*2:-n], temp.iloc[-n:]
    gap = recent["bidder_count"].mean() - old["bidder_count"].mean()
    status = "경쟁 심화" if gap >= 10 else "경쟁 완화" if gap <= -10 else "정체"
    return {"status":"산출완료", "bidder_status":status, "old_avg":old["bidder_count"].mean(), "recent_avg":recent["bidder_count"].mean(), "gap":gap}


def market_comment(status: str, trend: dict, volatility: dict, bidder: dict) -> str:
    comments = [f"현재 시장 상태는 '{status}'로 판단됩니다."]
    if trend.get("direction") == "저가화 진행": comments.append("최근 사정률이 이전 구간보다 낮아지는 흐름입니다.")
    elif trend.get("direction") == "보수화 진행": comments.append("최근 사정률이 이전 구간보다 높아지는 흐름입니다.")
    elif trend.get("direction") == "횡보": comments.append("최근 평균 흐름은 큰 방향성 없이 횡보 중입니다.")
    if volatility.get("volatility_status") == "변동 확대": comments.append("최근 변동성이 확대되어 단일 평균값 의존은 위험합니다.")
    elif volatility.get("volatility_status") == "안정화": comments.append("최근 변동성은 축소되어 비교적 안정적인 흐름입니다.")
    if bidder.get("bidder_status") == "경쟁 심화": comments.append("최근 업체수가 증가하여 실질 낙찰 난이도가 높아질 수 있습니다.")
    elif bidder.get("bidder_status") == "경쟁 완화": comments.append("최근 업체수는 감소하는 흐름입니다.")
    if status == "과열·고위험 시장": comments.append("공격형보다 구간을 좁히고 리스크를 우선 관리하는 전략이 필요합니다.")
    elif status == "주의 시장": comments.append("중립형 기준을 중심으로 최근 흐름 보정을 반영하는 것이 적합합니다.")
    elif status == "안정 시장": comments.append("기관 패턴이 유지된다면 안정형·중립형 전략 모두 검토 가능합니다.")
    return " ".join(comments)


def market_status(df: pd.DataFrame, n: int = 30) -> dict:
    trend = trend_direction(df, n)
    volatility = volatility_change(df, n)
    bidder = bidder_trend(df, n)
    score = 0
    if trend.get("direction") == "저가화 진행": score += 2
    elif trend.get("direction") == "보수화 진행": score += 1
    if volatility.get("volatility_status") == "변동 확대": score += 2
    elif volatility.get("volatility_status") == "안정화": score -= 1
    if bidder.get("bidder_status") == "경쟁 심화": score += 2
    elif bidder.get("bidder_status") == "경쟁 완화": score -= 1
    status = "과열·고위험 시장" if score >= 5 else "주의 시장" if score >= 3 else "관찰 시장" if score >= 1 else "안정 시장"
    return {"market_status":status, "trend":trend, "volatility":volatility, "bidder":bidder, "score":score, "comment":market_comment(status, trend, volatility, bidder)}
