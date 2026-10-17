import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR, MODEL_DIR, REPORT_DIR = ROOT / "data", ROOT / "models", ROOT / "reports"
for _d in (DATA_DIR, MODEL_DIR, REPORT_DIR):
    _d.mkdir(exist_ok=True)

MASTER_CSV = DATA_DIR / "clean_master.csv"
CHAIN_JSON = DATA_DIR / "chain.json"
MODEL_PATH = MODEL_DIR / "proofchain_model.joblib"

# In production keep this in a vault / HSM (on IBM Z: ICSF). Env var for the demo.
SECRET = os.environ.get("PROOFCHAIN_SECRET", "change-me-demo-key").encode()

DATE_COLS = ["Order_Date", "Ship_Date", "Last_Updated"]
REQUIRED = ["Row_ID", "Order_Date", "Ship_Date", "Sales",
            "Source_System", "Last_Modified_By", "Last_Updated"]
