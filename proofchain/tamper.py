"""Tamper simulators. Silent edits do NOT update provenance; legit_edit does."""
import numpy as np
import pandas as pd


def _pick(out, frac, rng):
    return rng.choice(out.index, size=max(1, int(len(out) * frac)), replace=False)


def change_values(df, frac=0.05, seed=None):
    rng = np.random.default_rng(seed); out = df.copy()
    idx = _pick(out, frac, rng)
    out.loc[idx, "Sales"] = (out.loc[idx, "Sales"] * rng.uniform(1.2, 1.6, len(idx))).round(2)
    return out


def drop_provenance(df, frac=0.1, seed=None):
    rng = np.random.default_rng(seed); out = df.copy()
    idx = _pick(out, frac, rng)
    out.loc[idx, rng.choice(["Source_System", "Last_Modified_By"])] = np.nan
    return out


def shift_dates(df, frac=0.05, seed=None):
    rng = np.random.default_rng(seed); out = df.copy()
    idx = _pick(out, frac, rng)
    out.loc[idx, "Last_Updated"] = out.loc[idx, "Ship_Date"] - pd.to_timedelta(rng.integers(1, 30, len(idx)), unit="D")
    half = idx[: len(idx) // 2]
    out.loc[half, "Ship_Date"] = out.loc[half, "Order_Date"] - pd.to_timedelta(rng.integers(1, 10, len(half)), unit="D")
    return out


def drop_or_duplicate_rows(df, frac=0.03, seed=None):
    rng = np.random.default_rng(seed); out = df.copy()
    idx = _pick(out, frac, rng)
    if rng.random() < 0.5:
        return out.drop(index=idx)
    return pd.concat([out, out.loc[idx]], ignore_index=True)


def legit_edit(df, frac=0.05, seed=None):
    """Documented change: data changes AND the paper trail is updated."""
    rng = np.random.default_rng(seed); out = df.copy()
    idx = _pick(out, frac, rng)
    out.loc[idx, "Sales"] = (out.loc[idx, "Sales"] * rng.uniform(0.8, 1.3, len(idx))).round(2)
    out.loc[idx, "Last_Updated"] = out.loc[idx, "Last_Updated"] + pd.Timedelta(days=20)
    out.loc[idx, "Last_Modified_By"] = rng.choice(["alice", "bob", "carol"], len(idx))
    return out


TAMPER_FNS = [change_values, drop_provenance, shift_dates, drop_or_duplicate_rows]
