from __future__ import annotations

import re
from typing import Dict

import numpy as np
import pandas as pd

from utils.constants import COLUMN_ALIASES, DEFAULT_RATE_RANGE

MIN_VALID_YEAR = 2000
MAX_FUTURE_YEAR_OFFSET = 1


def map_columns(df: pd.DataFrame) -> Dict[str, str]:
    mapping: Dict[str, str] = {}
    columns = [str(c).strip() for c in df.columns]
    original_by_clean = {str(c).strip(): c for c in df.columns}

    for std_col, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            if alias in columns:
                mapping[std_col] = original_by_clean[alias]
                break
    return mapping


def normalize_text(value):
    if pd.isna(value):
        return np.nan
    text = str(value).strip().replace("\u3000", " ")
    text = re.sub(r"\s+", " ", text)
    return text if text else np.nan


def normalize_agency(value):
    text = normalize_text(value)
    if pd.isna(text):
        return np.nan
    text = str(text)
    if text.startswith("한전"):
        text = text.replace("한전", "한국전력공사", 1)
    if text.startswith("한국전력 "):
        text = text.replace("한국전력", "한국전력공사", 1)
    return text.strip()


def normalize_company(value):
    text = normalize_text(value)
    if pd.isna(text):
        return np.nan
    for word in ["(주)", "㈜", "주식회사", "(유)", "유한회사", "합자회사", "합명회사"]:
        text = text.replace(word, "")
    text = re.sub(r"[\s·ㆍ\-_,.]+", "", text)
    return text.strip()


def normalize_category(value):
    text = normalize_text(value)
    if pd.isna(text):
        return np.nan
    text = str(text)
    if "감리" in text:
        return "전력감리"
    if "설계" in text:
        return "전력설계"
    if "건설사업관리" in text or "CM" in text.upper():
        return "건설사업관리"
    if "ENG" in text.upper() or "엔지니어링" in text:
        return "ENG"
    return text


def to_number(series: pd.Series) -> pd.Series:
    cleaned = (
        series.astype(str)
        .str.replace(",", "", regex=False)
        .str.replace("%", "", regex=False)
        .str.replace("원", "", regex=False)
        .str.strip()
    )
    cleaned = cleaned.replace({"": np.nan, "nan": np.nan, "None": np.nan})
    return pd.to_numeric(cleaned, errors="coerce")


def normalize_rate_scale(rate: pd.Series) -> pd.Series:
    """예가/기초 사정률을 분석용 0 기준 값으로 통일합니다.
    - 원본이 100.1234 형태면 +0.1234로 변환
    - 원본이 1.001234 형태면 +0.1234로 변환
    - 원본이 +0.1234 형태면 그대로 사용
    """
    r = rate.copy()
    valid = r.dropna()
    if valid.empty:
        return r
    med = float(valid.median())
    if 90 <= med <= 110:
        return r - 100
    if 0.9 <= med <= 1.1:
        return (r - 1) * 100
    return r


def clean_open_date(series: pd.Series) -> pd.Series:
    dates = pd.to_datetime(series, errors="coerce")
    current_year = pd.Timestamp.today().year
    valid_year = dates.dt.year.between(MIN_VALID_YEAR, current_year + MAX_FUTURE_YEAR_OFFSET)
    return dates.where(valid_year)


def clean_data(df: pd.DataFrame) -> tuple[pd.DataFrame, Dict[str, str]]:
    mapping = map_columns(df)
    out = df.copy()

    for std_col, src_col in mapping.items():
        out[std_col] = out[src_col]

    for col in ["agency", "winner", "category", "region", "notice_name"]:
        if col in out.columns:
            out[col] = out[col].apply(normalize_text)

    if "agency" in out.columns:
        out["agency_clean"] = out["agency"].apply(normalize_agency)
    if "winner" in out.columns:
        out["winner_clean"] = out["winner"].apply(normalize_company)
    if "category" in out.columns:
        out["category_clean"] = out["category"].apply(normalize_category)

    for col in ["base_price", "expected_price", "rate", "bidder_count"]:
        if col in out.columns:
            out[col] = to_number(out[col])

    if "rate" in out.columns:
        out["rate"] = normalize_rate_scale(out["rate"])

    if "open_date" in out.columns:
        out["open_date"] = clean_open_date(out["open_date"])

    if "rate" in out.columns:
        low, high = DEFAULT_RATE_RANGE
        out["rate_is_outlier"] = ~out["rate"].between(low, high)
    else:
        out["rate_is_outlier"] = False

    out["date_is_invalid"] = out["open_date"].isna() if "open_date" in out.columns else False
    out["bidder_count_is_invalid"] = (
        out["bidder_count"].isna() | (out["bidder_count"] < 1)
    ) if "bidder_count" in out.columns else False
    return out, mapping


def filtered_valid_rate(df: pd.DataFrame) -> pd.DataFrame:
    if "rate" not in df.columns:
        return df.copy()
    return df[df["rate"].notna() & (~df.get("rate_is_outlier", False))].copy()


def cleaning_report(df: pd.DataFrame) -> dict:
    return {
        "전체건수": int(len(df)),
        "사정률이상치": int(df.get("rate_is_outlier", pd.Series(False, index=df.index)).sum()),
        "날짜오류": int(df.get("date_is_invalid", pd.Series(False, index=df.index)).sum()),
        "업체수오류": int(df.get("bidder_count_is_invalid", pd.Series(False, index=df.index)).sum()),
        "정규화기관수": int(df["agency_clean"].nunique(dropna=True)) if "agency_clean" in df.columns else 0,
        "정규화업체수": int(df["winner_clean"].nunique(dropna=True)) if "winner_clean" in df.columns else 0,
        "정규화업종수": int(df["category_clean"].nunique(dropna=True)) if "category_clean" in df.columns else 0,
    }
