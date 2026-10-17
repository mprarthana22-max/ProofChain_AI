import html
import pandas as pd
from .chain import sha256_bytes
from .explain import explain
from .features import features

COLORS = {"READY": "#1a7f37", "NEEDS": "#b08800", "REJECT": "#cf222e"}


def assess(v, raw, master, chain, bundle, llm=None):
    """v = parsed DataFrame, raw = the file's exact bytes."""
    f = pd.DataFrame([features(v, master)])[bundle["columns"]]
    p_tamper = float(bundle["clf"].predict_proba(f)[0, 1])
    anomalous = bundle["iso"].predict(f)[0] == -1
    registered = chain.is_registered(raw)
    intact = chain.chain_intact()

    score = int(round((1 - p_tamper) * 100))
    score = max(score, 90) if registered else min(score, 60)   # unregistered can never be "ready"
    if not intact:
        score = 0
    verdict = ("READY FOR REVIEW" if score >= 80 else
               "NEEDS HUMAN VERIFICATION" if score >= 50 else "REJECT - LIKELY TAMPERED")

    r = f.iloc[0]
    why = []
    if not intact:
        why.append("the evidence chain itself has been modified")
    if not registered:
        why.append("file hash is not in the evidence chain")
    if r.silent_change_frac > 0:
        why.append(f"{r.silent_change_frac:.1%} of Sales values changed with no update trail")
    if r.prov_missing_frac > 0:
        why.append(f"{r.prov_missing_frac:.1%} of rows have missing provenance")
    if r.ship_before_order > 0:
        why.append(f"{r.ship_before_order:.1%} of rows ship before they were ordered")
    if r.updated_before_ship > 0:
        why.append(f"{r.updated_before_ship:.1%} of rows were 'updated' before shipping")
    if r.dup_ids > 0 or r.missing_rows_frac > 0:
        why.append("rows were duplicated or removed")
    if anomalous and not registered:
        why.append("isolation forest flags the pattern as anomalous")

    return {"score": score, "verdict": verdict, "why": why, "p_tamper": p_tamper,
            "registered": registered, "chain_intact": intact, "sha256": sha256_bytes(raw),
            "explanation": explain(score, verdict, why, llm)}


def card_html(res, name="file"):
    color = COLORS[res["verdict"].split()[0]]
    items = "".join(f"<li>{html.escape(w)}</li>" for w in res["why"]) or "<li>No issues found</li>"
    return f"""<div style="border:2px solid {color};border-radius:10px;padding:14px;margin:10px 0;max-width:720px;font-family:sans-serif">
<div style="font-size:15px;color:#888">{html.escape(name)}</div>
<div style="font-size:30px;font-weight:700;color:{color}">{res['score']}/100 &nbsp; {html.escape(res['verdict'])}</div>
<div style="margin-top:8px"><b>Findings</b><ul style="margin:4px 0">{items}</ul></div>
<div style="margin-top:8px"><b>AI explanation</b><br>{html.escape(res['explanation'])}</div>
<div style="margin-top:8px;font-size:12px;color:#888">SHA-256: {res['sha256'][:32]}... | registered in chain: {res['registered']} | chain intact: {res['chain_intact']}</div>
</div>"""
