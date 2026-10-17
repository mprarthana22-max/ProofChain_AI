"""Step 3 (CLI): check a file.   python verify.py data/demo_suspicious.csv
Register an approved file:      python verify.py data/new.csv --register "approved by alice"
Add --llm to use a local Hugging Face model for the explanation."""
import argparse
import io
from pathlib import Path
from proofchain.chain import EvidenceChain
from proofchain.config import MASTER_CSV, REPORT_DIR
from proofchain.data import load_csv
from proofchain.explain import make_llm
from proofchain.model import load_bundle
from proofchain.report import assess, card_html

ap = argparse.ArgumentParser()
ap.add_argument("file")
ap.add_argument("--register", metavar="NOTE", help="register this file as an approved version")
ap.add_argument("--llm", action="store_true")
a = ap.parse_args()

raw = Path(a.file).read_bytes()
v = load_csv(io.BytesIO(raw))
master, chain, bundle = load_csv(MASTER_CSV), EvidenceChain.load(), load_bundle()

if a.register:
    chain.register(raw, note=a.register, name=Path(a.file).name)
    print("registered", a.file)

res = assess(v, raw, master, chain, bundle, make_llm() if a.llm else None)
print(f"\n{Path(a.file).name}: TRUST {res['score']}/100 -> {res['verdict']}")
for w in res["why"]:
    print("  -", w)
print("\n" + res["explanation"])
(REPORT_DIR / "last_report.html").write_text(card_html(res, Path(a.file).name))
print("\nsaved reports/last_report.html")
