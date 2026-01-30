# Human-in-the-Loop Financial Document Summarizer

A **human-governed AI system** that summarizes financial PDF documents using an LLM, evaluates output quality using **deterministic scoring**, and requires **explicit human approval** before storing results in PostgreSQL.  
Designed for **auditability, traceability, and safe regeneration** using reviewer feedback.

---

## Why this project exists (Enterprise framing)

In regulated or high-risk workflows (finance, compliance, policy, reporting), an LLM must be treated as a **drafting assistant**, not a decision maker.

This system enforces:
- ✅ Human approval before persistence  
- ✅ Deterministic scoring (not “LLM judging LLM”)  
- ✅ Full traceability (model + prompt + decision logs)  
- ✅ Safe optional regeneration only via reviewer feedback  

---

## Architecture

> **Design principle:** Separation of generation, evaluation, and authority  
> - LLM generates drafts  
> - Deterministic logic evaluates quality  
> - Humans retain final authority  
> - All actions are logged and reproducible  

![Architecture Diagram](snapshots/architecture.png)

---

## Features

### 1) PDF → Text Extraction
- Extracts readable text from uploaded PDFs using `pdfplumber`.

### 2) LLM Summarization (Draft only)
- Calls OpenAI `chat.completions` (model: `gpt-4o-mini`) to generate a professional summary.

### 3) Deterministic Quality Scoring
Scores the generated summary using:
- **Coverage** (key financial topics present)
- **Clarity** (average sentence length heuristic)
- **Language quality** (formatting/grammar red flags)

Also flags:
- `flagged_uncertain` (e.g., “maybe”, “probably”, “I think”)
- `flagged_too_short` (less than 25 words)

### 4) Human-in-the-Loop Approval
Human reviewer decides:
- **Approve** → store in `approved_summaries`
- **Reject + Feedback** → store in `rejected_summaries`

### 5) Auditability & Traceability
Stores:
- decision outcome  
- flags + score  
- timestamps  
- model/prompt version (recommended)  

### 6) Optional Regeneration (Reviewer-driven only)
If rejected, feedback is saved and can be used to regenerate a better summary.
> The system explicitly avoids autonomous self-loops.

---

## Tech Stack

- Python
- `pdfplumber` (PDF extraction)
- OpenAI API (LLM summarization)
- PostgreSQL (approved/rejected storage)
- `python-dotenv` (.env loading)
- `psycopg2-binary` (DB operations)

---

## Folder Structure (suggested)

