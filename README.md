# Human-in-the-Loop Financial Document Summarizer

A **human-governed, audit-ready AI system** for summarizing financial PDF documents.  
The system uses an LLM strictly as a **drafting assistant**, applies **deterministic quality evaluation**, and enforces **explicit human approval** before any output is persisted.

This project is designed for **regulated, high-risk domains** such as finance, compliance, policy analysis, and executive reporting — where uncontrolled AI outputs are unacceptable.

---

## Why This Project Exists (Enterprise Context)

In real-world enterprise systems, **LLMs cannot be trusted as autonomous decision-makers**.

This project demonstrates how to design AI systems where:
- Generation, evaluation, and authority are **cleanly separated**
- Humans retain **final control**
- Every action is **traceable, reproducible, and auditable**
- Regeneration is **explicitly gated**, never automatic

> **Core philosophy:**  
> *LLMs generate drafts. Deterministic systems evaluate. Humans decide.*

---

## Architecture

**Design principle: Separation of generation, evaluation, and authority**

- LLM generates drafts only
- Deterministic logic evaluates quality
- Humans retain final authority
- All decisions are logged and reproducible

![Architecture Diagram](snapshots/architecture.png)

---

## System Flow (High Level)

1. **PDF ingestion**
2. **Text extraction**
3. **LLM-based summarization (draft)**
4. **Deterministic quality scoring**
5. **Optional PII / sensitive data checks**
6. **Human review (approve / reject)**
7. **Immutable persistence with full audit trail**
8. **Optional regeneration driven only by reviewer feedback**

There are **no autonomous loops** and **no self-approving AI paths**.

---

## Key Features

### 1. PDF → Text Extraction
- Extracts readable text from uploaded PDFs using `pdfplumber`
- Handles multi-page documents safely

---

### 2. LLM Summarization (Draft-Only)
- Uses OpenAI `chat.completions`
- Model: `gpt-4o-mini`
- The LLM **never writes directly to the database**
- Output is always treated as a *proposal*, not a decision

---

### 3. Deterministic Quality Scoring (No LLM Self-Judging)

Each summary is evaluated using **rule-based, explainable heuristics**:

**Coverage**
- Checks presence of key financial topics

**Clarity**
- Average sentence length heuristics

**Language Quality**
- Flags formatting / grammar red flags

**Hard Flags**
- `flagged_uncertain` (e.g. “maybe”, “probably”)
- `flagged_too_short` (< 25 words)

> This avoids the anti-pattern of *“LLM judging LLM output”*.

---

### 4. Human-in-the-Loop Approval (Authority Layer)

A human reviewer explicitly decides:

- **Approve**
  - Stored in `approved_summaries`
- **Reject + Feedback**
  - Stored in `rejected_summaries`

> No summary is persisted without human approval.

---

### 5. Auditability & Traceability (First-Class)

Every decision logs:
- UUID
- Timestamp
- Decision outcome
- Quality flags
- Model version
- Prompt version (recommended)

This enables:
- Compliance reviews
- Forensic audits
- Reproducibility of decisions

---

### 6. Reviewer-Gated Regeneration (Optional)

If a summary is rejected:
- Reviewer feedback is stored
- Regeneration is **explicitly triggered**
- The system **never self-loops**

> Regeneration is *reviewer-driven*, not AI-driven.

---

## Environment & Secrets Management

- Real secrets live in `.env` (excluded via `.gitignore`)
- Repository includes `.env.example` as a template
- Virtual environments are excluded (`venv/`)

This ensures:
- No credential leaks
- Easy onboarding for collaborators
- Enterprise-safe configuration practices

---

## Tech Stack

- **Language:** Python
- **LLM:** OpenAI (`gpt-4o-mini`)
- **PDF Processing:** `pdfplumber`
- **Database:** PostgreSQL
- **DB Driver:** `psycopg2-binary`
- **Config:** `python-dotenv`

---

## Suggested Folder Structure

