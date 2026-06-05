from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any

import pandas as pd
import streamlit as st

DEFAULT_SPREADSHEET_ID = "1zysN9SiYhz8g9lxABBXWiODDjYdtkUh53hfhbe03pg4"
HISTORY_SHEET = "1_낙찰이력"
PATTERN_SHEET = "2_발주처패턴"
STRATEGY_SHEET = "4_전략결과"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.readonly",
]


def _as_dict(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return {k: _as_dict(v) if hasattr(v, "items") else v for k, v in value.items()}
    if hasattr(value, "items"):
        return {k: _as_dict(v) if hasattr(v, "items") else v for k, v in value.items()}
    return {}


def _get_secret_dict(name: str) -> dict[str, Any]:
    try:
        return _as_dict(st.secrets.get(name, {}))
    except Exception:
        return {}


def _get_spreadsheet_id() -> str:
    cfg = _get_secret_dict("google_sheets")
    return (
        str(cfg.get("spreadsheet_id") or "").strip()
        or os.getenv("BID_DB_SPREADSHEET_ID", "").strip()
        or DEFAULT_SPREADSHEET_ID
    )


def _get_service_account_info() -> tuple[dict[str, Any] | None, str]:
    raw_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()
    if raw_json:
        try:
            return json.loads(raw_json), "GOOGLE_SERVICE_ACCOUNT_JSON"
        except json.JSONDecodeError as exc:
            return None, f"GOOGLE_SERVICE_ACCOUNT_JSON 파싱 오류: {exc}"

    raw_json_secret = ""
    try:
        raw_json_secret = str(st.secrets.get("gcp_service_account_json", "") or "").strip()
    except Exception:
        raw_json_secret = ""
    if raw_json_secret:
        try:
            return json.loads(raw_json_secret), "st.secrets.gcp_service_account_json"
        except json.JSONDecodeError as exc:
            return None, f"st.secrets.gcp_service_account_json 파싱 오류: {exc}"

    cfg = _get_secret_dict("google_sheets")
    cfg_raw_json = str(cfg.get("service_account_json") or "").strip()
    if cfg_raw_json:
        try:
            return json.loads(cfg_raw_json), "st.secrets.google_sheets.service_account_json"
        except json.JSONDecodeError as exc:
            return None, f"st.secrets.google_sheets.service_account_json 파싱 오류: {exc}"

    info = _get_secret_dict("gcp_service_account")
    if info:
        return info, "st.secrets.gcp_service_account"

    nested = cfg.get("service_account")
    if isinstance(nested, dict) and nested:
        return nested, "st.secrets.google_sheets.service_account"

    service_keys = {"type", "project_id", "private_key", "client_email", "token_uri"}
    if service_keys.issubset(set(cfg)):
        return {k: v for k, v in cfg.items() if k != "spreadsheet_id"}, "st.secrets.google_sheets"

    return None, "서비스계정 정보 없음"


def google_sheets_config_status() -> dict[str, Any]:
    info, source = _get_service_account_info()
    return {
        "spreadsheet_id": _get_spreadsheet_id(),
        "has_service_account": bool(info),
        "service_account_source": source,
    }


def _client():
    try:
        import gspread
        from google.oauth2.service_account import Credentials
    except Exception as exc:
        raise RuntimeError(
            "gspread/google-auth 패키지가 필요합니다. requirements.txt에 gspread와 google-auth를 추가하세요."
        ) from exc

    info, source = _get_service_account_info()
    if not info:
        raise RuntimeError(f"Google Sheets 서비스계정이 설정되지 않았습니다. ({source})")

    if "private_key" in info and isinstance(info["private_key"], str):
        info["private_key"] = info["private_key"].replace("\\n", "\n")

    credentials = Credentials.from_service_account_info(info, scopes=SCOPES)
    return gspread.authorize(credentials)


def _to_float(value: Any, default: float = 0.0) -> float:
    if value is None:
        return default
    text = str(value).strip().replace(",", "").replace("%", "")
    if not text:
        return default
    try:
        return float(text)
    except ValueError:
        return default


def _to_int(value: Any, default: int = 0) -> int:
    return int(round(_to_float(value, float(default))))


def _records_to_df(records: list[dict[str, Any]]) -> pd.DataFrame | None:
    if not records:
        return None
    df = pd.DataFrame(records)
    if df.empty:
        return None
    df = df.dropna(how="all")
    return df if not df.empty else None


def _pattern_records_to_stats(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    stats: dict[str, dict[str, Any]] = {}
    for row in records:
        org = str(row.get("발주기관", "")).strip()
        if not org:
            continue
        n = _to_int(row.get("표본수"))
        stats[org] = {
            "pred": _to_float(row.get("예측값")),
            "conservative": _to_float(row.get("보수")),
            "aggressive": _to_float(row.get("공격")),
            "trend": str(row.get("트렌드") or "보합"),
            "pattern": str(row.get("패턴") or "무작위"),
            "grade": str(row.get("신뢰등급") or ("D" if n < 5 else "C")),
            "mae": _to_float(row.get("MAE"), 0.5),
            "n": n,
            "mean": _to_float(row.get("평균")),
            "std": _to_float(row.get("표준편차"), 0.5),
            "r5": _to_float(row.get("최근5평균")),
            "r10": _to_float(row.get("최근10평균")),
            "r20": _to_float(row.get("최근20평균")),
            "w5": 0.25,
            "w10": 0.20,
            "wm": 0.55,
            "recent10": [],
            "source": "Google Sheets DB",
        }
    return stats


@st.cache_data(ttl=600, show_spinner=False)
def _load_reference_cached(spreadsheet_id: str) -> tuple[pd.DataFrame | None, dict[str, dict[str, Any]], dict[str, Any]]:
    sheet = _client().open_by_key(spreadsheet_id)
    history_ws = sheet.worksheet(HISTORY_SHEET)
    pattern_ws = sheet.worksheet(PATTERN_SHEET)

    history_df = _records_to_df(history_ws.get_all_records())
    pattern_stats = _pattern_records_to_stats(pattern_ws.get_all_records())
    status = {
        "connected": True,
        "spreadsheet_id": spreadsheet_id,
        "spreadsheet_title": sheet.title,
        "history_rows": 0 if history_df is None else len(history_df),
        "pattern_count": len(pattern_stats),
        "loaded_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    return history_df, pattern_stats, status


def load_google_sheets_reference(force_refresh: bool = False) -> tuple[pd.DataFrame | None, dict[str, dict[str, Any]], dict[str, Any]]:
    spreadsheet_id = _get_spreadsheet_id()
    config = google_sheets_config_status()
    if not config["has_service_account"]:
        return None, {}, {
            "connected": False,
            "spreadsheet_id": spreadsheet_id,
            "configured": False,
            "error": "Google Sheets 서비스계정이 아직 설정되지 않았습니다.",
            **config,
        }
    if force_refresh:
        _load_reference_cached.clear()
    try:
        return _load_reference_cached(spreadsheet_id)
    except Exception as exc:
        return None, {}, {
            "connected": False,
            "configured": True,
            "spreadsheet_id": spreadsheet_id,
            "error": str(exc),
            **config,
        }


def strategy_records_for_sheet(results: list[dict[str, Any]], created_by: str = "") -> list[list[Any]]:
    today = datetime.now().strftime("%Y-%m-%d")
    rows: list[list[Any]] = []
    for row in results:
        bid = row["bid"]
        a1, a2, a3 = row.get("a1"), row.get("a2"), row.get("a3")
        tp = row.get("three_pt")
        rows.append([
            today,
            bid.get("no"),
            bid.get("bid_no", ""),
            bid.get("name", ""),
            bid.get("org", ""),
            bid.get("base", 0),
            a1.get("pred") if a1 else "",
            a2.get("pred") if a2 else "",
            a3.get("pred") if a3 else "",
            row.get("range_lo") if row.get("range_lo") is not None else "",
            row.get("range_hi") if row.get("range_hi") is not None else "",
            tp.get("pt_a") if tp else "",
            tp.get("pt_b") if tp else "",
            tp.get("pt_c") if tp else "",
            tp.get("cover") if tp else "",
            a1.get("grade") if a1 else "",
            "",
            created_by,
        ])
    return rows


def append_strategy_results(results: list[dict[str, Any]], created_by: str = "") -> dict[str, Any]:
    spreadsheet_id = _get_spreadsheet_id()
    sheet = _client().open_by_key(spreadsheet_id)
    ws = sheet.worksheet(STRATEGY_SHEET)
    rows = strategy_records_for_sheet(results, created_by)
    if not rows:
        return {"saved": 0}
    ws.append_rows(rows, value_input_option="USER_ENTERED")
    return {"saved": len(rows), "spreadsheet_id": spreadsheet_id, "sheet": STRATEGY_SHEET}
