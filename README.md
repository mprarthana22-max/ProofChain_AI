# Datathon

**Team:** 404! Founders | **IBM Z Datathon 2026** | **Event code:** SSF2026
**Challenge:** AI Secured: Innovation Without Exposure

# ProofChain AI

>AI that decides whether digital evidence is trustworthy enough to use.
Built for the IBM Z Datathon 2026 (theme: AI Secured - Innovation Without Exposure). Event code: SSF2026

## Problem
Organizations make decisions from spreadsheets and reports, but a value can be silently changed, a source can go missing, or two versions can conflict, and nobody notices until the decision is wrong. A plain "the file differs" check can't tell a legitimate, documented edit from a silent one.

## What it does
1. **Hash chain** - SHA-256 of each approved file, linked and HMAC-signed. Any change to a file is detected.
2. **Feature extraction** - compares a received report to the registered master (changed values, missing provenance, impossible dates, duplicated/removed rows).
3. **ML** - Random Forest (documented vs silent change) + Isolation Forest (anomaly check), scikit-learn.
4. **Trust score and verdict** - READY / NEEDS HUMAN VERIFICATION / REJECT. A file that is not in the chain can never be "ready".
5. **Explanation** - plain-English reason (optional local LLM; it only sees the findings, never the data).

Dataset: public Superstore sales data. `Source_System`, `Last_Modified_By`, `Last_Updated` are **simulated** provenance metadata added by `prepare_data.py`.

## Run it
```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python prepare_data.py path/to/superstore.csv   # 1. builds data/clean_master.csv
python train.py                                 # 2. trains models, registers master, makes demo files
python verify.py data/demo_suspicious.csv       # 3. -> REJECT
python verify.py data/demo_approved.csv         #    -> READY FOR REVIEW
python evaluate.py                              # 4. recall table + ML vs hash chain
streamlit run app.py                            # 5. upload UI
```
Register a new approved version: `python verify.py data/new.csv --register "approved by alice"`.
Optional LLM explanation: `pip install transformers torch`, then `python verify.py FILE --llm` or tick the box in the app.

## Run on IBM LinuxONE
Open the project on the LinuxONE VM (VS Code Remote-SSH, or upload the folder to Jupyter Lab and use its terminal), create the venv and run the same commands. Check `python -c "import platform; print(platform.machine())"` prints `s390x`, and screenshot it for the demo.

## Project layout
```
proofchain/   config, data, tamper, features, chain, model, explain, report
prepare_data.py  train.py  verify.py  evaluate.py  app.py
data/ models/ reports/   (generated)
```

## Open-source libraries

pandas, numpy, scikit-learn, joblib, streamlit, hashlib/hmac (Python standard library), optional: transformers (google/flan-t5-base).
=======
# ProofChain_AI

IBM Z/Linuxone
