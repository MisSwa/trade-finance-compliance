# Tech Stack

## Hard Constraints

These are non-negotiable for this project:

| Constraint | Reason |
|---|---|
| **Claude / Anthropic API only** — no other LLM providers | Consistency of model behaviour for compliance reasoning; single vendor for security review |
| **LangSmith only** for observability and evaluation | No Datadog, Sentry, or other APM tools in v1 |
| **No external databases** | In-memory state only; no persistent storage in v1 |
| **Python 3.11+** | Required for `TypedDict` features, `tomllib`, and modern `asyncio` used throughout |

---

## Stack

### Language & Runtime

- **Python 3.11+**
- Virtual environment via `venv` or `conda`

### AI & Orchestration

| Component | Library | Notes |
|---|---|---|
| LLM | `langchain-anthropic` | `ChatAnthropic` wrapping Claude claude-sonnet-4-5 |
| Model | `claude-claude-sonnet-4-5` (configurable via `COMPLIANCE_MODEL` env var) | claude-sonnet-4-5 for all agents; override for testing |
| Agent orchestration | `langgraph >= 0.2` | StateGraph with parallel fan-out, `interrupt()` for HITL |
| Graph state persistence | `langgraph.checkpoint.memory.MemorySaver` | In-memory only; thread-safe for single-server demo |
| Structured output | `ChatAnthropic.with_structured_output(PydanticModel)` | Forces agents to return typed Pydantic objects |
| Tracing & evaluation | `langsmith >= 0.2` | Full trace of every agent run; eval datasets in LangSmith UI |

### UI

| Component | Library | Notes |
|---|---|---|
| Web app framework | `streamlit >= 1.35` | Single-file app; handles file upload, session state, and page rendering without a separate backend |
| Session state | `st.session_state` | Persists graph thread ID, interrupt data, and final report across Streamlit reruns within a session |
| File upload | `st.file_uploader` | Native multi-file uploader; no `python-multipart` needed |
| Background execution | `threading.Thread` | Graph runs in a daemon thread; Streamlit polls via `st.rerun()` until complete or interrupted |

### Document Processing

| Component | Library | Notes |
|---|---|---|
| PDF text extraction | `pypdf >= 4.3` | Extracts text from digital PDFs |
| Scanned PDF note | Not supported in v1 | If `pypdf` yields < 100 chars, agent will flag as unreadable and escalate to human review |

### State Management

**`TypedDict` is the canonical state container for this project.** All graph state flows through a single `ComplianceState(TypedDict)` that is the source of truth at every node.

| Component | Library | Notes |
|---|---|---|
| Graph state | `typing_extensions.TypedDict` | `ComplianceState` carries all data between nodes; LangGraph reads/writes it directly |
| Agent output types | `pydantic >= 2.9` | Used only for `ChatAnthropic.with_structured_output()` — forces the LLM to return a typed object; the result is then unpacked into `ComplianceState` fields |
| Type hints | `typing` stdlib | `Optional`, `Literal`, `list` used inside TypedDict field definitions |

**Why TypedDict over Pydantic for state?** LangGraph's `StateGraph` expects a plain `TypedDict` (or dataclass). Using TypedDict keeps state manipulation simple: nodes return plain dicts of the fields they update, and LangGraph merges them. Pydantic validation is reserved for the LLM boundary only.

### Observability & Logging

| Component | Library | Notes |
|---|---|---|
| Structured logging | `structlog >= 24` | JSON-structured logs; sensitive fields are SHA256-hashed, never logged in plain text |
| Tracing | LangSmith via `LANGCHAIN_TRACING_V2=true` | Agent-level spans, latency, token usage |
| Evaluation | LangSmith Datasets + Evaluators | Accuracy of verdict classification measured against labelled test cases |

### Configuration

| Component | Library | Notes |
|---|---|---|
| Env vars | `python-dotenv` | `.env` file for API keys and tunable parameters |
| Key parameters | See table below | All tunable without code changes |

#### Configurable Parameters (`.env`)

```
ANTHROPIC_API_KEY=                  # Required
LANGCHAIN_API_KEY=                  # Required for LangSmith
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=trade-finance-compliance
COMPLIANCE_MODEL=claude-claude-sonnet-4-5  # Anthropic model ID
CONFIDENCE_THRESHOLD=0.7            # Below this → human review
MAX_FILE_SIZE_MB=20
UPLOAD_DIR=./uploads
LOG_LEVEL=INFO
```

---

## Architecture Diagram

```
                        ┌─────────────────────────────────────────┐
                        │             Streamlit App                │
                        │  Upload · Processing · Review · Report  │
                        └──────────────┬──────────────────────────┘
                                       │
                        ┌──────────────▼──────────────────────────┐
                        │          LangGraph Workflow              │
                        │                                          │
                        │   START → Document Extractor             │
                        │               │                          │
                        │    ┌──────────┼──────────┐              │
                        │    ▼          ▼           ▼             │
                        │ Sanctions  Policy    Consistency         │
                        │ Screener   Checker   Checker             │
                        │    └──────────┬──────────┘              │
                        │               ▼                          │
                        │          Risk Scorer                     │
                        │               │                          │
                        │    ┌──────────▼──────────┐              │
                        │    │   Confidence < 0.7  │              │
                        │    │   OR verdict ≠ clear │              │
                        │    └──┬──────────────┬───┘              │
                        │       │ YES           │ NO               │
                        │       ▼               ▼                  │
                        │  Human Review   Report Generator         │
                        │  (interrupt)          │                  │
                        │       └───────────────┘                  │
                        │               ▼                          │
                        │             END                          │
                        └─────────────────────────────────────────┘
                                       │
                        ┌──────────────▼──────────────────────────┐
                        │              LangSmith                   │
                        │   Traces · Token usage · Eval datasets   │
                        └─────────────────────────────────────────┘
```

---

## Privacy Model

Logs **never** contain:
- Company / entity names
- Transaction amounts or currencies
- Account numbers or IBAN/SWIFT codes
- Port names, vessel names, country names
- Personal names

Logs **may** contain:
- Event types (`document_extracted`, `sanctions_hit_found`)
- Counts (`sanctions_hits=2`)
- SHA256 hash references for cross-event correlation (`entity_ref=[ENTITY:a3f2c1d4]`)
- Verdict labels (`verdict=needs_review`)
- Error codes and latency metrics

The compliance **report** shown to the officer in the web UI contains full information — this is by design. The privacy constraint applies only to application logs and LangSmith trace metadata.

---

## Validation

### 1. Input Validation

Enforced in the Streamlit UI **before** the graph thread is started. The graph never receives invalid input.

| Rule | Check | Failure behaviour |
|---|---|---|
| File type | Each uploaded file must have a `.pdf` extension and a `application/pdf` MIME type | Show inline error; block submission |
| File size | Each file must be ≤ `MAX_FILE_SIZE_MB` (default 20 MB) | Show inline error; block submission |
| Minimum document set | At least one trade document must be uploaded (Bill of Lading, Invoice, or Packing List) | Show inline error; block submission |
| PDF readability | After extraction via `pypdf`, the text content must be ≥ 100 characters | Allowed to proceed, but `extraction_confidence` is set to `0.0` and the case is immediately routed to human review with a message explaining the document could not be read |
| Policy document | Optional; if uploaded it must also pass file type and size checks | Same inline error as above |

### 2. Agent Output Validation

Each agent calls Claude via `with_structured_output(PydanticModel)`. LangChain enforces the schema at the LLM boundary. Additional runtime checks are applied after the call returns.

**Confidence threshold gate**

Every agent output carries a `confidence: float` field in `[0.0, 1.0]`. After the Risk Scorer aggregates findings into `overall_confidence`, the routing logic applies:

```
overall_confidence < CONFIDENCE_THRESHOLD (default 0.7)  →  human_review node
verdict in {"needs_review", "rejected"}                  →  human_review node
verdict == "clear" AND confidence >= 0.7                 →  report_generator node
```

**Per-agent required fields**

| Agent | Required output fields | If missing or malformed |
|---|---|---|
| Document Extractor | `doc_type`, `extraction_confidence` | Set `extraction_confidence=0.0`; route to human review |
| Sanctions Screener | `is_clear`, `confidence`, `summary` | Set `confidence=0.0`; route to human review |
| Policy Checker | `is_clear`, `confidence`, `summary` | Set `confidence=0.0`; route to human review |
| Consistency Checker | `is_clear`, `confidence`, `summary` | Set `confidence=0.0`; route to human review |
| Risk Scorer | `score`, `verdict`, `confidence` | Route to human review; log `risk_scorer_failed` event |
| Report Generator | `verdict`, `risk_score`, `recommendations` | Surface error to UI; do not show partial report |

**Structured output failure handling**

If `with_structured_output()` raises a validation or parsing exception:
1. The exception is caught inside the agent node function
2. A privacy-safe error event is logged (`agent_output_invalid`, agent name, no PII)
3. The node returns a minimal state update setting `confidence=0.0` and `errors` appended
4. The graph continues to the Risk Scorer which routes to human review

No unhandled exception from an agent should ever surface to the user as a raw traceback.

### 3. Evaluation & Test Strategy

Implemented in Phase 5 using LangSmith.

**Test dataset**

A labelled dataset of sample cases stored in LangSmith under the project `trade-finance-compliance`. Each case contains:
- Input: set of document text strings (simulating extracted PDF content)
- Expected output: `verdict` label — `"clear"`, `"needs_review"`, or `"rejected"`

Minimum dataset size for v1: **15 cases** (5 per verdict class).

**Evaluator**

A custom LangSmith evaluator (`verdict_accuracy`) that compares `compliance_report.verdict` against the expected label. Returns a binary score: `1` (correct) or `0` (incorrect).

**Target accuracy for v1 demo**

| Metric | Target |
|---|---|
| Overall verdict accuracy | ≥ 85% on the labelled dataset |
| `rejected` recall | ≥ 95% — missing a rejection is the highest-risk failure |
| `clear` precision | ≥ 80% — too many false positives overloads human reviewers |

**Running evaluation**

```bash
python scripts/run_eval.py
```

Results appear in the LangSmith UI under Evaluations for project `trade-finance-compliance`. CI can be added in a later phase to gate on these numbers.

---

### 4. Pytest — Unit & Integration Tests

**Libraries**

| Library | Version | Purpose |
|---|---|---|
| `pytest` | `>= 8.0` | Test runner |
| `pytest-mock` | `>= 3.14` | `mocker` fixture for patching LLM calls without `unittest.mock` boilerplate |
| `pytest-asyncio` | `>= 0.23` | For any async graph or tool calls |

**Test directory layout**

```
tests/
├── conftest.py                        # shared fixtures (mock LLM, sample state, sample docs)
├── fixtures/
│   ├── sample_invoice.txt             # extracted text of a clean invoice
│   ├── sample_bol.txt                 # extracted text of a clean Bill of Lading
│   ├── sample_flagged_invoice.txt     # invoice with a sanctioned entity name
│   └── sample_policy.txt             # minimal bank policy text
├── unit/
│   ├── tools/
│   │   ├── test_pdf_reader.py         # extraction, < 100 char handling
│   │   └── test_watchlist.py          # entity lookup, fuzzy matching
│   ├── models/
│   │   └── test_schemas.py            # TypedDict construction, Pydantic field constraints
│   └── agents/
│       ├── test_document_extractor.py
│       ├── test_sanctions_screener.py
│       ├── test_policy_checker.py
│       ├── test_consistency_checker.py
│       ├── test_risk_scorer.py
│       └── test_report_generator.py
└── integration/
    ├── test_graph_routing.py          # clear → report_generator, rejected → human_review
    └── test_graph_hitl.py             # interrupt fires, Command(resume=...) resumes correctly
```

**Mocking strategy**

All LLM calls are mocked in unit and integration tests. No real API calls are made during `pytest`.

```python
# conftest.py pattern
@pytest.fixture
def mock_llm(mocker):
    mock = mocker.patch("app.agents.document_extractor.ChatAnthropic")
    mock.return_value.with_structured_output.return_value.invoke.return_value = DocumentData(
        doc_type="invoice",
        extraction_confidence=0.95,
        ...
    )
    return mock
```

LangSmith tracing is disabled in the test environment via:
```
LANGCHAIN_TRACING_V2=false   # set in pytest.ini or conftest.py os.environ
```

**Test markers**

```ini
# pytest.ini
[pytest]
markers =
    unit: fast, fully mocked, no API calls
    integration: mocked LLM but runs full LangGraph graph
    llm: makes real Anthropic API calls (skipped by default in CI)
```

Run only fast tests: `pytest -m "not llm"`
Run everything including real LLM calls: `pytest -m llm --run-llm`

**Key things each layer must test**

| Layer | Must verify |
|---|---|
| Unit — tools | PDF returns empty string gracefully; watchlist returns correct hit severity |
| Unit — agents | Each node returns the correct TypedDict keys; low-confidence LLM response triggers `confidence=0.0` |
| Unit — risk scorer | All routing conditions: clear+high-confidence, clear+low-confidence, needs_review, rejected |
| Integration — routing | Graph takes the correct edge after risk scorer for each verdict/confidence combination |
| Integration — HITL | `interrupt()` fires when expected; `Command(resume=...)` unblocks the graph and final state is correct |

---

### 5. UI Testing — Streamlit

Streamlit's built-in `AppTest` (from `streamlit.testing.v1`) is used for UI tests. No browser or Playwright needed — `AppTest` runs the Streamlit script in-process and exposes all widgets as Python objects.

**Library**

`AppTest` ships with `streamlit >= 1.28`. No additional package required.

**Test file**

```
tests/ui/
└── test_streamlit_app.py
```

**What UI tests cover**

| Test | What it checks |
|---|---|
| `test_upload_view_renders` | App starts in `idle` state; file uploader and submit button are present |
| `test_submit_blocked_without_files` | Submit button does nothing if no files are attached; error message shown |
| `test_invalid_file_type_rejected` | Uploading a `.docx` shows an inline error and does not change status |
| `test_oversized_file_rejected` | File exceeding `MAX_FILE_SIZE_MB` shows size error |
| `test_processing_view_shown` | After valid upload, status transitions to `processing` and spinner is visible |
| `test_review_view_renders` | When `st.session_state.status = "awaiting_review"` is pre-set, review widgets render correctly |
| `test_decision_submit` | Selecting a decision and clicking confirm updates `st.session_state` with the correct decision value |
| `test_report_view_renders` | When `st.session_state.status = "completed"` with a mock report, report content is displayed |
| `test_error_view_renders` | When status is `error`, error message is shown and restart button is present |

**Pattern — pre-seeding session state**

```python
from streamlit.testing.v1 import AppTest
from unittest.mock import patch

def test_review_view_renders():
    at = AppTest.from_file("streamlit_app.py")
    at.session_state["status"] = "awaiting_review"
    at.session_state["interrupt_data"] = {
        "verdict": "needs_review",
        "risk_score": 0.72,
        "sanctions_summary": "One watchlist hit found.",
        ...
    }
    at.run()
    assert at.radio[0].label == "Decision"
    assert "needs_review" in at.markdown[0].value.lower()
```

**Running UI tests**

```bash
pytest tests/ui/           # UI tests only
pytest tests/              # all tests (mocked LLM)
pytest tests/ -m llm       # all tests including real API calls
```
