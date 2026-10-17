"""Step 1: turn the original Superstore CSV into data/clean_master.csv (adds simulated provenance).
Usage: python prepare_data.py path/to/superstore.csv"""
import sys
import numpy as np
import pandas as pd
from proofchain.config import MASTER_CSV

if len(sys.argv) < 2:
    sys.exit("Usage: python prepare_data.py path/to/superstore.csv")

for enc in ("utf-8", "cp1252", "latin-1"):
    try:
        df = pd.read_csv(sys.argv[1], encoding=enc)
        print("read file with encoding:", enc)
        break
    except UnicodeDecodeError:
        continue
df.columns = [c.replace(" ", "_").replace("-", "_") for c in df.columns]
df["Order_Date"] = pd.to_datetime(df["Order_Date"], dayfirst=True)
df["Ship_Date"] = pd.to_datetime(df["Ship_Date"], dayfirst=True)

# SIMULATED provenance metadata (say so in the video): Superstore has none of its own
rng = np.random.default_rng(42)
df["Source_System"] = "ERP-Finance"
df["Last_Modified_By"] = rng.choice(["alice", "bob", "carol"], len(df))
df["Last_Updated"] = df["Ship_Date"] + pd.to_timedelta(rng.integers(1, 10, len(df)), unit="D")

df.to_csv(MASTER_CSV, index=False)
print("saved", MASTER_CSV, df.shape)
print("ship before order:", int((df["Ship_Date"] < df["Order_Date"]).sum()))
