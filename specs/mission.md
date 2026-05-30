# Mission

## Problem

Trade finance compliance is document-heavy, time-sensitive, and high-stakes. Compliance officers at banks manually review stacks of PDFs — Bills of Lading, Invoices, Packing Lists — checking for sanctions exposure, internal policy violations, and cross-document inconsistencies. This process is slow, error-prone under volume, and difficult to audit.

A single missed sanctions hit or document discrepancy can result in regulatory penalties, reputational damage, or unwitting facilitation of financial crime.

## What We Are Building

A multi-agent AI system that assists compliance officers in reviewing trade finance transactions. The system:

- Accepts PDF trade documents (Bill of Lading, Commercial Invoice, Packing List) and optionally a bank policy document
- Runs specialized AI agents in parallel to screen for sanctions exposure, policy violations, and document inconsistencies
- Produces a structured compliance verdict: **Clear**, **Needs Review**, or **Rejected** — with full reasoning
- Routes uncertain or flagged cases to a compliance officer for human review before finalising a decision
- Generates a detailed, auditable compliance report

## Target Audience

| Audience | Role | How they use the system |
|---|---|---|
| **Compliance Officer** | Primary user | Uploads trade documents, reviews AI findings, makes final approve/reject/escalate decisions |
| **Trade Finance Analyst** | Primary user | Interprets flagged discrepancies and sanctions hits; adds review notes to the compliance report |
| **Compliance Manager** | Secondary user | Reviews completed reports; oversees escalated cases; responsible for SAR filing decisions |
| **Internal Audit** | Tertiary user | Accesses audit trail and LangSmith traces to verify that decisions were made correctly and consistently |

All users are trained bank staff operating within an existing compliance framework. The system is a decision-support tool — it does not replace their professional judgement or legal accountability.

## v1 Success Criterion

The system can be demonstrated end-to-end using sample trade documents:
- A compliance officer uploads PDFs via a web interface
- All agents run and produce findings
- A flagged case pauses for human review and accepts the officer's decision
- A compliance report is generated with the final verdict and supporting evidence

This is a working prototype that proves the architecture. Production hardening (auth, persistent storage, live sanctions APIs) is explicitly out of scope for v1.

## Core Principles

| Principle | What it means in practice |
|---|---|
| **Human in the loop** | No transaction is auto-approved or auto-rejected without an analyst having the ability to intervene. High-risk or low-confidence cases always pause for review. |
| **Graceful degradation** | If an agent produces low-confidence output (below threshold), the system escalates to human review rather than producing a wrong verdict. |
| **Privacy by design** | Trade documents contain confidential financial data. Application logs must never contain entity names, amounts, account numbers, or personal identifiers. Sensitive fields are one-way hashed for log correlation only. |
| **Auditability** | Every decision — automated or human — is traceable. LangSmith captures the full reasoning chain of every agent run. |
| **Accuracy over speed** | Compliance accuracy is non-negotiable. Speed is optimised within that constraint, primarily through parallel agent execution. |

## Regulatory Context

The system is designed to support compliance with **FATF (Financial Action Task Force)** recommendations, specifically:

- FATF Recommendation 6: Targeted financial sanctions related to terrorism and proliferation financing
- FATF Recommendation 10: Customer due diligence in trade finance
- FATF Guidance on Trade-Based Money Laundering (TBML): detecting over/under-invoicing, phantom shipments, and multiple invoicing

The system does not replace a bank's legal compliance obligations. It is a decision-support tool for trained compliance officers.

## Out of Scope — v1

- Live integration with OFAC, EU, or HMT sanctions APIs (mock data used)
- User authentication and role-based access control
- Persistent storage or case management database
- Automated SAR (Suspicious Activity Report) filing
- Integration with core banking systems (SWIFT, trade finance platforms)
- Multi-language document support
