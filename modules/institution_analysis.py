from __future__ import annotations

import pandas as pd


def analyze_agency(df: pd.DataFrame, min_count: int = 5) -> pd.DataFrame:
    agency_col = "agency_clean" if "agency_clean" in df.columns else "agency"
    if agency_col not in df.columns or "rate" not in df.columns:
        return pd.DataFrame()
    stats = (
        df.dropna(subset=[agency_col, "rate"])
        .groupby(agency_col)
        .agg(건수=("rate", "size"), 평균사정률=("rate", "mean"), 중앙사정률=("rate", "median"), 표준편차=("rate", "std"))
        .reset_index()
        .rename(columns={agency_col: "agency"})
    )
    stats = stats[stats["건수"] >= min_count].copy()
    if stats.empty:
        return stats
    stats["안정도"] = stats["표준편차"].fillna(0).apply(lambda v: "안정" if v <= 0.25 else "보통" if v <= 0.45 else "분산")
    return stats.sort_values(["건수", "표준편차"], ascending=[False, True]).round(4)


def agency_strategy_comment(row: pd.Series) -> str:
    mean = row.get("평균사정률", 0)
    std = row.get("표준편차", 0)
    stability = row.get("안정도", "")
    direction = "양수권" if mean > 0.1 else "음수권" if mean < -0.1 else "중립권"
    return f"{row.get('agency')}는 표본 {int(row.get('건수', 0)):,}건 기준 {direction} 성향이며, 변동성은 {stability}입니다. 평균 {mean:+.4f}%, 표준편차 {std:.4f}%를 기준으로 보수/공격 구간을 나눠 확인하세요."
