"""Trade Finance Compliance — Streamlit UI."""
import os
import time
import uuid

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from app import runner, state_store  # noqa: E402

_MAX_BYTES = int(os.environ.get("MAX_FILE_SIZE_MB", "20")) * 1024 * 1024
_UPLOAD_DIR = os.environ.get("UPLOAD_DIR", "./uploads")


# ---------------------------------------------------------------------------
# Session helpers
# ---------------------------------------------------------------------------

def _session_id() -> str:
    if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())
    return st.session_state.session_id


def _reset(sid: str) -> None:
    state_store.clear_session(sid)
    st.session_state.session_id = str(uuid.uuid4())
    st.rerun()


# ---------------------------------------------------------------------------
# Views
# ---------------------------------------------------------------------------

def _upload_view(sid: str) -> None:
    st.subheader("Upload Trade Documents")

    trade_files = st.file_uploader(
        "Trade documents (Bill of Lading, Invoice, Packing List)",
        type=["pdf"],
        accept_multiple_files=True,
        key="trade_docs",
    )
    policy_file = st.file_uploader(
        "Bank policy document (optional)",
        type=["pdf"],
        accept_multiple_files=False,
        key="policy_doc",
    )

    if st.button("Run Compliance Check", key="submit"):
        if not trade_files:
            st.error("Please upload at least one trade document.")
            return

        for f in trade_files:
            if f.size > _MAX_BYTES:
                st.error(
                    f"{f.name} exceeds the {os.environ.get('MAX_FILE_SIZE_MB', '20')} MB limit."
                )
                return

        os.makedirs(_UPLOAD_DIR, exist_ok=True)
        document_paths: list[str] = []
        for f in trade_files:
            dest = os.path.join(_UPLOAD_DIR, f"{sid}_{f.name}")
            with open(dest, "wb") as fh:
                fh.write(f.getbuffer())
            document_paths.append(dest)

        policy_path: str | None = None
        if policy_file:
            dest = os.path.join(_UPLOAD_DIR, f"{sid}_policy_{policy_file.name}")
            with open(dest, "wb") as fh:
                fh.write(policy_file.getbuffer())
            policy_path = dest

        runner.run_in_background(sid, document_paths, policy_path)
        state_store.set_session(sid, status="processing")
        st.rerun()


def _processing_view() -> None:
    st.info("Running compliance analysis. This may take a moment...")
    time.sleep(2)
    st.rerun()


def _review_view(sid: str, session: dict) -> None:
    st.subheader("Human Review Required")

    data = session.get("interrupt_data") or {}
    verdict = data.get("verdict", "needs_review")
    score = data.get("score", 0.0)
    confidence = data.get("confidence", 0.0)
    risk_factors = data.get("risk_factors") or []

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Risk Score", f"{score:.2f}")
    with col2:
        st.metric("Confidence", f"{confidence:.2f}")

    colour = {"clear": "green", "needs_review": "orange", "rejected": "red"}.get(verdict, "orange")
    st.markdown(f"**Verdict:** :{colour}[{verdict.upper().replace('_', ' ')}]")

    if risk_factors:
        st.subheader("Risk Factors")
        for factor in risk_factors:
            st.warning(factor)

    st.divider()
    st.subheader("Your Decision")
    decision = st.radio("Decision", ["Approve", "Reject", "Escalate"], key="decision_radio")
    st.text_area("Notes (optional)", key="review_notes")

    if st.button("Confirm Decision", key="confirm"):
        thread_id = session.get("thread_id") or sid
        runner.resume_review(sid, decision.lower(), thread_id)
        state_store.set_session(sid, status="processing")
        st.rerun()


def _report_view(sid: str, session: dict) -> None:
    st.subheader("Compliance Report")

    final_state = session.get("final_state") or {}
    report = final_state.get("compliance_report")

    if report is not None:
        verdict      = report.verdict      if hasattr(report, "verdict")      else report.get("verdict", "unknown")
        risk_score   = report.risk_score   if hasattr(report, "risk_score")   else report.get("risk_score", 0.0)
        recs         = report.recommendations if hasattr(report, "recommendations") else report.get("recommendations", [])
        sar          = report.sar_warranted if hasattr(report, "sar_warranted") else report.get("sar_warranted", False)
        reasoning    = report.reasoning    if hasattr(report, "reasoning")    else report.get("reasoning", "")
        audit        = report.audit_summary if hasattr(report, "audit_summary") else report.get("audit_summary", "")

        colour = {"clear": "green", "needs_review": "orange", "rejected": "red"}.get(verdict, "orange")
        st.markdown(f"### Verdict: :{colour}[{verdict.upper().replace('_', ' ')}]")
        st.metric("Risk Score", f"{risk_score:.2f}")

        if sar:
            st.error("SAR filing should be considered for this transaction.")

        st.subheader("Recommendations")
        for rec in recs:
            st.write(f"- {rec}")

        st.subheader("Reasoning")
        st.write(reasoning)

        st.subheader("Audit Summary")
        st.write(audit)

        report_text = (
            f"COMPLIANCE REPORT\n\nVerdict: {verdict}\nRisk Score: {risk_score:.2f}\n"
            f"SAR Warranted: {sar}\n\nRecommendations:\n"
            + "\n".join(f"- {r}" for r in recs)
            + f"\n\nReasoning:\n{reasoning}\n\nAudit Summary:\n{audit}"
        )
        st.download_button(
            "Download Report",
            data=report_text,
            file_name="compliance_report.txt",
            mime="text/plain",
            key="download_report",
        )
    else:
        st.warning("Report not available.")

    if st.button("Start New Review", key="restart"):
        _reset(sid)


def _error_view(sid: str) -> None:
    st.error("An error occurred during document processing. Please try again.")
    if st.button("Start New Review", key="restart"):
        _reset(sid)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    st.title("Trade Finance Compliance Review")

    sid = _session_id()
    session = state_store.get_session(sid)
    status = session.get("status", "idle")

    if status == "idle":
        _upload_view(sid)
    elif status == "processing":
        _processing_view()
    elif status == "awaiting_review":
        _review_view(sid, session)
    elif status == "completed":
        _report_view(sid, session)
    elif status == "error":
        _error_view(sid)


main()
