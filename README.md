# Trade Finance Compliance

A multi-agent AI system that assists compliance officers in reviewing trade finance transactions. The system accepts PDF trade documents, runs specialized agents in parallel to screen for sanctions exposure, policy violations, and document inconsistencies, and produces an auditable compliance verdict — **Clear**, **Needs Review**, or **Rejected**.

Uncertain or flagged cases are routed to a compliance officer for human review before a final decision is made.

---

## Overview

**Agents:**

| Agent | What it does |
|---|---|
| Document Extractor | Reads PDFs and extracts structured fields (buyer, seller, goods, ports, vessel, amounts) via Claude |
| Sanctions Screener | Checks all extracted entities against a mock sanctions watchlist; uses Claude to produce a structured assessment |
| Policy Checker | Validates the transaction against bank policy rules using Claude |
| Consistency Checker | Detects cross-field inconsistencies that may indicate fraud or TBML |
| Risk Scorer | Aggregates findings into a numeric risk score and verdict (rule-based, no LLM) |
| Report Generator | Produces the final auditable compliance report including regulatory recommendations |

**Routing:**

- `rejected` or `needs_review` verdict → human review (graph pauses for officer decision)
- `clear` but confidence < 0.7 → human review
- `clear` and confidence ≥ 0.7 → automated report

---

## Setup

```bash
git clone <repo>
cd trade-finance-compliance

python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env
# Edit .env and fill in:
#   ANTHROPIC_API_KEY=...
#   LANGCHAIN_API_KEY=...       (required for LangSmith tracing and live eval)
#   COMPLIANCE_MODEL=claude-sonnet-4-5
```

---

## Running the demo

```bash
streamlit run streamlit_app.py
```

Open `http://localhost:8501` in your browser. The expected flow:

1. **Upload** — drop one or more trade document PDFs (invoice, bill of lading, packing list) and optionally a policy PDF
2. **Processing** — agents run in parallel; progress is shown live
3. **Review** (flagged cases) — risk findings are displayed; select Approve / Reject / Escalate and add notes
4. **Report** — full compliance report with verdict, risk factors, and regulatory recommendations; downloadable as text

---

## CLI mode

```bash
python main.py path/to/invoice.pdf
python main.py path/to/invoice.pdf path/to/bill_of_lading.pdf --policy path/to/policy.pdf
```

Prints the extracted `DocumentData` as JSON and exits with code 1 if extraction confidence is 0.0 (unreadable PDF).

---

## Viewing LangSmith traces

Set `LANGCHAIN_TRACING_V2=true` in your `.env` file (it is `false` by default). All subsequent graph runs will appear in the LangSmith UI under the project name configured in `LANGCHAIN_PROJECT`.

1. Log in to [smith.langchain.com](https://smith.langchain.com)
2. Navigate to **Projects** → your project name
3. Each run shows the full reasoning chain for every agent

---

## Running tests

```bash
# All tests (unit + integration — no real API calls)
pytest

# Unit tests only
pytest tests/unit/ -v

# Integration tests only
pytest tests/integration/ -v

# UI tests only
pytest tests/ui/ -v
```

All tests mock LLM calls. No `ANTHROPIC_API_KEY` is required to run the test suite.

---

## Running evaluation

**Local dry-run (required for merge gate — no API calls):**

```bash
LANGCHAIN_TRACING_V2=false python scripts/run_eval.py --dry-run
```

Expected output:

```
Running evaluation in dry-run mode (no LangSmith API calls)...
  Case case-a-clear (clear): PASS
  Case case-b-rejected (rejected): PASS
  Case case-c-needs-review (needs_review): PASS
Evaluation complete. Accuracy: 3/3 cases matched.
```

**Live LangSmith evaluation (requires `LANGCHAIN_API_KEY`):**

```bash
python scripts/run_eval.py
```

Results appear in the LangSmith UI under the `trade-finance-compliance-v1` dataset → **Experiments**.

---

## Architecture

```
Streamlit UI (streamlit_app.py)
    │
    ├── Background thread (app/runner.py)
    │       └── run_graph() / resume with Command
    │
    └── LangGraph workflow (app/graph/workflow.py)
            │
            ├── document_extractor   ──────────────────────┐
            ├── [parallel]                                  │
            │   ├── sanctions_screener                      │
            │   ├── policy_checker                          ▼
            │   └── consistency_checker        risk_scorer (rule-based)
            │                                       │
            │                           ┌───────────┴───────────┐
            │                      human_review          report_generator
            │                      (interrupt)                   │
            │                           └───────────────────────►│
            │                                                     ▼
            └─────────────────────────────────────── ComplianceReport
```

**State:** `ComplianceState` TypedDict flows through all nodes. The `errors` field uses `Annotated[list, operator.add]` so parallel agents can each append errors without write conflicts.

**Privacy:** Logs never contain entity names, amounts, or account numbers. Sensitive fields are SHA-256 hashed with `[ENTITY:hash]` format for log correlation only.

**Observability:** LangSmith captures the full reasoning chain of every agent run when `LANGCHAIN_TRACING_V2=true`.
