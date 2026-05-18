from __future__ import annotations

import pandas as pd
import streamlit as st


@st.cache_data(show_spinner=False)
def load_excel(uploaded_file) -> pd.DataFrame:
    """Streamlit 업로드 엑셀 파일을 DataFrame으로 읽습니다."""
    return pd.read_excel(uploaded_file, engine="openpyxl")


@st.cache_data(show_spinner=False)
def load_excel_from_path(path: str) -> pd.DataFrame:
    """로컬 경로 엑셀 파일을 DataFrame으로 읽습니다."""
    return pd.read_excel(path, engine="openpyxl")
