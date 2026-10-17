import pandas as pd
from .config import DATE_COLS, REQUIRED


def check_schema(df):
    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        raise ValueError(f"Not a ProofChain report. Missing columns: {missing}")


def load_csv(path_or_buffer):
    df = pd.read_csv(path_or_buffer)
    check_schema(df)
    for c in DATE_COLS:
        df[c] = pd.to_datetime(df[c])
    return df


def df_bytes(df):
    """Bytes of a dataframe exactly as it would be saved to CSV."""
    return df.to_csv(index=False).encode()
