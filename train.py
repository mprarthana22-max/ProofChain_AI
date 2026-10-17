"""Step 2: build 200 labelled versions, train the models, register the master, create demo files.
Usage: python train.py"""
import io
from proofchain.chain import EvidenceChain
from proofchain.config import DATA_DIR, MASTER_CSV, REPORT_DIR
from proofchain.data import df_bytes, load_csv
from proofchain.model import build_dataset, save_bundle, train
from proofchain.tamper import change_values, drop_provenance, legit_edit

master = load_csv(MASTER_CSV)
print("master:", master.shape)

feat = build_dataset(master)
feat.to_csv(REPORT_DIR / "features.csv", index=False)
bundle, report, cm, importances = train(feat)
save_bundle(bundle)
text = f"{report}\nConfusion matrix:\n{cm}\n\nFeature importance:\n{importances}\n"
(REPORT_DIR / "metrics.txt").write_text(text)
print(text)

# Fresh evidence chain: register the original master file (exact bytes)
chain = EvidenceChain()
chain.blocks = []
chain.register(MASTER_CSV.read_bytes(), note="original master", name=MASTER_CSV.name)

# Demo files
approved = legit_edit(master, 0.03, seed=7)
suspicious = change_values(drop_provenance(master, 0.1, seed=3), 0.05, seed=3)
(DATA_DIR / "demo_master.csv").write_bytes(MASTER_CSV.read_bytes())
(DATA_DIR / "demo_approved.csv").write_bytes(df_bytes(approved))
(DATA_DIR / "demo_suspicious.csv").write_bytes(df_bytes(suspicious))
chain.register((DATA_DIR / "demo_approved.csv").read_bytes(), note="approved correction by alice", name="demo_approved.csv")
print("chain blocks:", len(chain.blocks), "| intact:", chain.chain_intact())
print("Demo files in", DATA_DIR)
