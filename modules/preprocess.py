from __future__ import annotations

import re
from typing import Dict

import numpy as np
import pandas as pd

from utils.constants import COLUMN_ALIASES, DEFAULT_RATE_RANGE


def map_columns(df: pd.DataFrame) -> Dict[str, str]:
    """원본 컬럼명을 표준 컬럼명으로 매핑합니다."""
    mapping: Dict[str, str] = {}
    columns = list(df.columns)
    for std_col, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            if alias in columns:
                mapping[std_col] = alias
                break
    return mapping


def normalize_text(value):
    if pd.isna(value):
        return np.nan
    text = str(value).strip()
    text = re.sub(r"\s+", " ", text)
    return text


def to_number(series: pd.Series) -> pd.Series:
    return pd.to_numeric(
        series.astype(str).str.replace(",", "", regex=False).str.replace("%", "", regex=False),
        errors="coerce",
    )


def clean_data(df: pd.DataFrame) -> tuple[pd.DataFrame, Dict[str, str]]:
    mapping = map_columns(df)
    out = df.copy()

    for std_col, src_col in mapping.items():
        out[std_col] = out[src_col]

    for col in ["agency", "winner", "category", "region", "notice_name"]:
        if col in out.columns:
            out[col] = out[col].apply(normalize_text)

    for col in ["base_price", "expected_price", "rate", "bidder_count"]:
        if col in out.columns:
            out[col] = to_number(out[col])

    if "open_date" in out.columns:
        out["open_date"] = pd.to_datetime(out["open_date"], errors="coerce")
        # 비정상 미래 날짜 제거: 현재년도 + 1 초과는 오류 가능성이 높음
        current_year = pd.Timestamp.today().year
        out.loc[out["open_date"].dt.year > current_year + 1, "open_date"] = pd.NaT

    if "rate" in out.columns:
        low, high = DEFAULT_RATE_RANGE
        out["rate_is_outlier"] = ~out["rate"].between(low, high)
    else:
        out["rate_is_outlier"] = False

    return out, mapping


def filtered_valid_rate(df: pd.DataFrame) -> pd.DataFrame:
    if "rate" not in df.columns:
        return df.copy()
    return df[df["rate"].notna() & (~df.get("rate_is_outlier", False))].copy()
