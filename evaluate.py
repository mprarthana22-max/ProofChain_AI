"""Step 4: honest evaluation. Recall by tamper type/size, false alarms, ML vs hash chain.
Usage: python evaluate.py"""
import numpy as np
import pandas as pd
from proofchain.chain import EvidenceChain
from proofchain.config import MASTER_CSV, REPORT_DIR
from proofchain.data import df_bytes, load_csv
from proofchain.features import features
from proofchain.model import load_bundle
from proofchain.tamper import TAMPER_FNS, legit_edit

master, chain, bundle = load_csv(MASTER_CSV), EvidenceChain.load(), load_bundle()


def ml_flag(v):
    f = pd.DataFrame([features(v, master)])[bundle["columns"]]
    return int(bundle["clf"].predict(f)[0])


rows = []
for fn in TAMPER_FNS:
    for fr in [0.001, 0.005, 0.01, 0.05]:
        r = []
        for j in range(20):
            v = fn(master, fr, seed=7000 + j)
            r.append((ml_flag(v), int(not chain.is_registered(df_bytes(v)))))
        rows.append({"tamper": fn.__name__, "fraction": fr,
                     "ML only": np.mean([a for a, _ in r]),
                     "Hash only": np.mean([b for _, b in r]),
                     "ML OR hash": np.mean([a or b for a, b in r])})
table = pd.DataFrame(rows)
fp = np.mean([ml_flag(legit_edit(master, f, seed=9000 + j)) for j, f in enumerate(np.linspace(0.005, 0.1, 20))])
out = table.to_string(index=False) + f"\n\nFALSE ALARM RATE on legitimate edits (ML): {fp:.0%}\n"
print(out)
(REPORT_DIR / "evaluation.txt").write_text(out)
