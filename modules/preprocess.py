from __future__ import annotations

import re
from typing import Any

import pandas as pd


COLUMN_ALIASES = {
    "no": ["번호", "No", "순번"],
    "name": ["공고명", "사업명", "용역명"],
    "bid_no": ["공고번호", "입찰공고번호"],
    "agency": ["발주기관", "수요기관", "기관명"],
    "base_amount": ["기초금액", "기초가격", "추정가격"],
    "planned_amount": ["예정가격", "예정가"],
    "winner_amount": ["1순위투찰금액", "낙찰금액", "투찰금액"],
    "winner_rate": ["1순위기초대비", "투찰률", "낙찰률"],
    "winner": ["1순위업체", "낙찰업체", "업체명"],
    "business_no": ["1순위사업자번호", "사업자번호"],
    "winner_adj_rate": ["1순위사정율(0%)", "1순위사정율", "사정율"],
    "rate": ["예가/기초(0%)", "예가/기초(%)", "예가/기초", "사정률"],
    "open_date": ["개찰일", "개찰일시", "입찰일"],
    "category": ["업종", "분야", "업종명"],
    "bidder_count": ["업체수", "참여업체수", "입찰업체수"],
}


def _norm_header(value: Any) -> str:
    return re.sub(r"\s+", "", str(value or "").strip())


def _find_column(columns: list[str], aliases: list[str]) -> str | None:
    normalized = {_norm_header(col): col for col in columns}
    for alias in aliases:
        found = normalized.get(_norm_header(alias))
        if found:
            return found
    return None


def _to_number(series: pd.Series) -> pd.Series:
    return pd.to_numeric(
        series.astype(str)
        .str.replace(",", "", regex=False)
        .str.replace("%", "", regex=False)
        .str.strip(),
        errors="coerce",
    )


def _normalize_rate(series: pd.Series) -> pd.Series:
    rate = _to_number(series)
    median = rate.dropna().median() if rate.notna().any() else 0
    if 90 <= median <= 110:
        rate = rate - 100
    elif 0.9 <= median <= 1.1:
        rate = (rate - 1) * 100
    return rate


def _parse_date(series: pd.Series) -> pd.Series:
    text = series.astype(str).str.strip()
    parsed = pd.to_datetime(text, errors="coerce")
    short = parsed.isna() & text.str.match(r"^\d{2}\.\d{1,2}\.\d{1,2}$", na=False)
    if short.any():
        parsed.loc[short] = pd.to_datetime("20" + text.loc[short], format="%Y.%m.%d", errors="coerce")
    return parsed


def clean_data(raw_df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    df = raw_df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    mapping: dict[str, Any] = {"columns": {}, "missing": []}

    for standard, aliases in COLUMN_ALIASES.items():
        source = _find_column(list(df.columns), aliases)
        if source:
            df[standard] = df[source]
            mapping["columns"][standard] = source
        else:
            mapping["missing"].append(standard)

    if "rate" in df.columns:
        df["rate"] = _normalize_rate(df["rate"])
    if "base_amount" in df.columns:
        df["base_amount"] = _to_number(df["base_amount"])
    if "planned_amount" in df.columns:
        df["planned_amount"] = _to_number(df["planned_amount"])
    if "winner_amount" in df.columns:
        df["winner_amount"] = _to_number(df["winner_amount"])
    if "winner_rate" in df.columns:
        df["winner_rate"] = _to_number(df["winner_rate"])
    if "bidder_count" in df.columns:
        df["bidder_count"] = _to_number(df["bidder_count"])
    if "open_date" in df.columns:
        df["open_date"] = _parse_date(df["open_date"])

    for col in ["agency", "name", "category", "winner"]:
        if col in df.columns:
            clean_col = f"{col}_clean"
            df[clean_col] = df[col].astype(str).str.strip()

    return df, mapping


def filtered_valid_rate(df: pd.DataFrame, limit: float = 10.0) -> pd.DataFrame:
    if "rate" not in df.columns:
        return pd.DataFrame(columns=df.columns)
    out = df[df["rate"].notna() & df["rate"].between(-limit, limit)].copy()
    return out.reset_index(drop=True)


def cleaning_report(df: pd.DataFrame) -> dict[str, Any]:
    return {
        "rows": int(len(df)),
        "valid_rate_rows": int(df["rate"].notna().sum()) if "rate" in df.columns else 0,
        "agency_count": int(df["agency_clean"].nunique()) if "agency_clean" in df.columns else 0,
        "category_count": int(df["category_clean"].nunique()) if "category_clean" in df.columns else 0,
        "date_min": str(df["open_date"].min().date()) if "open_date" in df.columns and df["open_date"].notna().any() else None,
        "date_max": str(df["open_date"].max().date()) if "open_date" in df.columns and df["open_date"].notna().any() else None,
    }
