import pandas as pd
from typing import Dict, List

def summarize_counts(df: pd.DataFrame, columns: List[str]) -> Dict[str, Dict]:
    out = {}
    for col in columns:
        try:
            out[col] = df[col].value_counts(dropna=False).to_dict()
        except Exception:
            out[col] = {}
    return out