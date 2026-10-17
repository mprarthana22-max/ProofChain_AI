import csv
import hashlib
import io
import re
from pathlib import Path

import streamlit as st
from pypdf import PdfReader
from docx import Document

from proofchain.chain import EvidenceChain
from proofchain.config import MASTER_CSV, REPORT_DIR
from proofchain.data import load_csv
from proofchain.explain import make_llm
from proofchain.model import load_bundle
from proofchain.report import assess, card_html
import hashlib

# Initialize Streamlit session state
if "integrity_verified" not in st.session_state:
    st.session_state.integrity_verified = False
    
def calculate_sha256(file_bytes):
    """Calculate the SHA-256 hash of a document."""
    return hashlib.sha256(file_bytes).hexdigest()

def verify_integrity(file_bytes, registered_hash):
    """Compare a document's hash with its registered original hash."""
    current_hash = calculate_sha256(file_bytes)

    is_verified = (
        current_hash.lower()
        == registered_hash.strip().lower()
    )

    return {
        "current_hash": current_hash,
        "verified": is_verified
    }

st.set_page_config(page_title="ProofChain AI", page_icon="🔗")


@st.cache_resource
def load_static():
    return load_csv(MASTER_CSV), load_bundle()


@st.cache_resource
def get_llm():
    return make_llm()


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def extract_text(filename, raw):
    """Extract readable text from supported document formats."""
    suffix = Path(filename).suffix.lower()

    if suffix == ".txt":
        return raw.decode("utf-8", errors="replace")

    if suffix == ".csv":
        text = raw.decode("utf-8-sig", errors="replace")
        rows = list(csv.reader(io.StringIO(text)))
        return "\n".join(" | ".join(row) for row in rows)

    if suffix == ".pdf":
        reader = PdfReader(io.BytesIO(raw))
        return "\n".join(page.extract_text() or "" for page in reader.pages)

    if suffix == ".docx":
        doc = Document(io.BytesIO(raw))
        paragraphs = [p.text for p in doc.paragraphs]
        for table in doc.tables:
            for row in table.rows:
                paragraphs.append(" | ".join(cell.text for cell in row.cells))
        return "\n".join(paragraphs)

    raise ValueError("Unsupported file type.")


def numeric_values(text):
    """Extract numeric values for a basic comparison, not semantic validation."""
    return re.findall(r"(?<!\w)[+-]?\d[\d,]*(?:\.\d+)?%?(?!\w)", text)


def calculate_trust_score(
    conflicts,
    missing_fields,
    sources_found,
    integrity_verified=False,
    sources_verified=False,
):
    """
    Demo scoring model.
    Unverified checks do not receive full credit.
    """
    score = 100

    # Comparison: maximum deduction of 35 points
    score -= min(conflicts * 10, 25)
    score -= min(missing_fields * 5, 10)

    # Sources: deduct points if no source references are detected
    if not sources_found:
        score -= 25
    elif not sources_verified:
        score -= 10

    # Integrity: require a trusted registered hash
    if not integrity_verified:
        score -= 20

    score = max(0, min(100, score))

    if score >= 80 and integrity_verified and sources_verified:
        verdict = "READY"
    elif score >= 50:
        verdict = "NEEDS REVIEW"
    else:
        verdict = "REJECT"

    st.subheader("Evidence Trust Assessment")
    st.metric("Evidence Trust Score", f"{score}/100")

    if verdict == "READY":
        st.success(f"Verdict: {verdict}")
    elif verdict == "NEEDS REVIEW":
        st.warning(f"Verdict: {verdict}")
    else:
        st.error(f"Verdict: {verdict}")

    st.caption(
        "Prototype score based on configured rules. "
        "It is not a probability of authenticity or proof of fraud."
    )

    return {"score": score, "verdict": verdict}


import difflib


def compare_documents(name_a, text_a, name_b, text_b):
    """Compare reports by field name rather than line position."""
    import re

    def extract_fields(text):
        fields = {}
        for line in text.splitlines():
            if ":" not in line:
                continue

            key, value = line.split(":", 1)
            key = key.strip().lower()
            value = value.strip()

            if key and value:
                fields[key] = value

        return fields

    fields_a = extract_fields(text_a)
    fields_b = extract_fields(text_b)

    st.subheader("Document comparison")
    st.write(f"**Reference report:** {name_a}")
    st.write(f"**Compared report:** {name_b}")

    all_keys = sorted(set(fields_a) | set(fields_b))
    matches = []
    conflicts = []
    missing = []

    for key in all_keys:
        value_a = fields_a.get(key)
        value_b = fields_b.get(key)

        if value_a is None:
            missing.append((key, "reference", value_b))
        elif value_b is None:
            missing.append((key, "compared", value_a))
        elif value_a.casefold() == value_b.casefold():
            matches.append((key, value_a))
        else:
            conflicts.append((key, value_a, value_b))

    st.markdown("### Comparison summary")
    col1, col2, col3 = st.columns(3)
    col1.metric("Matching fields", len(matches))
    col2.metric("Conflicting fields", len(conflicts))
    col3.metric("Missing fields", len(missing))

    if matches:
        with st.expander("Matching fields", expanded=True):
            for key, value in matches:
                st.write(f"✅ **{key.title()}:** {value}")

    if conflicts:
        st.markdown("### Conflicting fields")
        for key, value_a, value_b in conflicts:
            left, right = st.columns(2)
            with left:
                st.markdown(f"🔴 **{key.title()} — Reference**")
                st.write(value_a)
            with right:
                st.markdown(f"🟠 **{key.title()} — Compared**")
                st.write(value_b)

    if missing:
        st.markdown("### Missing fields")
        for key, missing_from, available_value in missing:
            if missing_from == "reference":
                st.warning(
                    f"**{key.title()}** is missing from the reference report. "
                    f"Compared report value: {available_value}"
                )
            else:
                st.warning(
                    f"**{key.title()}** is missing from the compared report. "
                    f"Reference report value: {available_value}"
                )

    if not conflicts and not missing:
        st.success("All detected fields match.")

    return {
    "conflicts": len(conflicts),
    "missing_fields": len(missing),
    "matches": len(matches),
}

    st.info(
        "Differences and missing fields require review. "
        "They do not, by themselves, prove malicious tampering."
    )

st.subheader("🔐 SHA-256 Integrity Verification")

uploaded_integrity_file = st.file_uploader(
    "Upload a document to verify",
    type=["pdf", "docx", "txt", "csv"],
    key="integrity_upload"
)

registered_hash = st.text_input(
    "Enter the registered original SHA-256 hash",
    placeholder="Paste the original hash here"
)

if st.button("Verify Document Integrity"):
    if uploaded_integrity_file is None:
        st.warning("Please upload a document first.")

    elif not registered_hash.strip():
        st.warning("Please enter the registered original hash.")

    else:
        file_bytes = uploaded_integrity_file.getvalue()

        result = verify_integrity(
            file_bytes,
            registered_hash
        )

        integrity_verified = result["verified"]

        st.write("**Current SHA-256 Hash:**")
        st.code(result["current_hash"])

        if result["verified"]:
            st.session_state.integrity_verified = True
            st.success("Integrity verified!")
        else:
            st.session_state.integrity_verified = False
            st.error("Integrity check failed!")

        if "integrity_verified" not in st.session_state:
            st.session_state.integrity_verified = False

def check_sources(text):
    """Identify source references that may need verification."""
    patterns = [
        r"https?://\S+",
        r"Source\s*:\s*.+",
        r"Reference\s*:\s*.+",
        r"References\s*:\s*.+",
        r"Citation\s*:\s*.+",
    ]

    found = []

    for pattern in patterns:
        found.extend(re.findall(pattern, text, flags=re.IGNORECASE))

    # Remove duplicates while preserving order
    found = list(dict.fromkeys(found))

    st.subheader("Source verification")
    if found:
        st.write("Source references detected:")
        for source in found:
            st.write(f"- {source}")

        st.warning(
            "References were detected, but their authenticity "
            "has not yet been independently verified."
        )
    else:
        st.warning(
            "No recognizable source references were detected. "
            "Review whether this report needs supporting evidence."
        )

    return found

st.title("🔗 ProofChain AI")
st.caption(
    "Document integrity and evidence review on IBM LinuxONE. "
    "Upload ordinary reports or assess a compatible registered CSV."
)

with st.sidebar:
    st.subheader("Evidence chain")
    try:
        chain = EvidenceChain.load()
        st.write(f"Chain blocks: **{len(chain.blocks)}**")
        st.write(f"Chain intact: **{chain.chain_intact()}**")
    except Exception as exc:
        chain = None
        st.warning(f"Evidence chain unavailable: {exc}")

    use_llm = st.checkbox(
        "Use local LLM for explanation (may be slow)",
        value=False,
    )

st.subheader("Upload reports")
st.write("Upload one report for analysis, or two reports to compare.")

uploads = st.file_uploader(
    "Select report files",
    type=["pdf", "docx", "txt", "csv"],
    accept_multiple_files=True,
    help="Supported formats: PDF, DOCX, TXT and CSV.",
)

if uploads:
    documents = []

    for up in uploads[:2]:
        raw = up.getvalue()
        try:
            text = extract_text(up.name, raw)
        except Exception as exc:
            st.error(f"Could not read {up.name}: {exc}")
            continue

        item = {
            "name": up.name,
            "raw": raw,
            "text": text,
            "hash": sha256(raw),
        }
        documents.append(item)

        with st.expander(f"File details: {up.name}", expanded=True):
            st.write(f"**File size:** {len(raw):,} bytes")
            st.write(f"**SHA-256:** `{item['hash']}`")
            st.write(f"**Extracted characters:** {len(text):,}")
            if not text.strip():
                st.warning(
                    "No readable text was extracted. This may be a scanned PDF "
                    "or an unsupported document structure."
                )

    if len(uploads) > 2:
        st.info("For this version, only the first two uploaded files are processed.")

    if len(documents) == 2:
        comparison = compare_documents(
            documents[0]["name"],
            documents[0]["text"],
            documents[1]["name"],
            documents[1]["text"],
        )

        calculate_trust_score(
            conflicts=comparison["conflicts"],
            missing_fields=comparison["missing_fields"],
            sources_found=1 if "source:" in (documents[0]["text"] + documents[1]["text"]).lower()
                                or "reference:" in (documents[0]["text"] + documents[1]["text"]).lower()
                                else 0,
            integrity_verified=st.session_state.integrity_verified,
            sources_verified=False,
        )

    if len(documents) == 1:
        doc = documents[0]
        st.subheader("Single-document review")
        st.write("The file hash has been calculated.")
        st.info(
            "A hash alone cannot establish authenticity. Upload a trusted reference "
            "or a second report to compare content."
        )

        with st.expander("Preview extracted text"):
            st.text(doc["text"][:12000] or "No readable text extracted.")

        check_sources(doc["text"])

    # Preserve the existing assessment for CSVs that match the project's schema.
    compatible_csvs = [
        item for item in documents
        if Path(item["name"]).suffix.lower() == ".csv"
    ]

    if compatible_csvs:
        st.subheader("ProofChain registered-data assessment")
        st.caption(
            "This assessment requires a CSV matching your existing project schema."
        )

        selected_name = st.selectbox(
            "Choose CSV for registered-data assessment",
            [item["name"] for item in compatible_csvs],
        )
        selected = next(
            item for item in compatible_csvs
            if item["name"] == selected_name
        )

        if st.button("Run ProofChain assessment"):
            try:
                master, bundle = load_static()
                v = load_csv(io.BytesIO(selected["raw"]))

                res = assess(
                    v,
                    selected["raw"],
                    master,
                    chain,
                    bundle,
                    get_llm() if use_llm else None,
                )

                verdict_key = res["verdict"].split()[0]
                color = {
                    "READY": "green",
                    "NEEDS": "orange",
                    "REJECT": "red",
                }.get(verdict_key, "blue")

                st.markdown(
                    f"## :{color}[{res['score']}/100 - {res['verdict']}]"
                )
                st.subheader("Findings")
                for finding in res["why"] or ["No issues found"]:
                    st.write("- " + finding)

                st.subheader("AI explanation")
                st.info(res["explanation"])

                st.caption(
                    f"SHA-256 {res['sha256'][:32]}... | "
                    f"registered: {res['registered']} | "
                    f"chain intact: {res['chain_intact']}"
                )

                REPORT_DIR.mkdir(parents=True, exist_ok=True)
                report_html = card_html(res, selected["name"])
                (REPORT_DIR / "last_report.html").write_text(
                    report_html, encoding="utf-8"
                )
                st.download_button(
                    "Download assessment report (HTML)",
                    data=report_html,
                    file_name="proofchain_assessment.html",
                    mime="text/html",
                )

                if not res["registered"] and chain is not None:
                    with st.expander(
                        "Approve this version (register in the evidence chain)"
                    ):
                        note = st.text_input(
                            "Approval note",
                            "approved by reviewer",
                        )
                        if st.button("Register as approved"):
                            chain.register(
                                selected["raw"],
                                note=note,
                                name=selected["name"],
                            )
                            st.success(
                                "Registered. Re-upload the file to reassess it."
                            )

            except Exception as exc:
                st.error(
                    "The file could be read as a document, but the registered-data "
                    f"assessment could not process it: {exc}"
                )
                st.info(
                    "Check whether this CSV uses the column structure expected "
                    "by your existing ProofChain project."
                )
