from __future__ import annotations

import pandas as pd


def load_excel(uploaded_file) -> pd.DataFrame:
    return pd.read_excel(uploaded_file)
