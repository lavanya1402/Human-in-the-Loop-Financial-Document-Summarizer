# Human-in-the-Loop Financial Document Summarizer

A **human-governed, audit-ready AI system** for summarizing financial PDF documents.  
The system uses an LLM strictly as a **drafting assistant**, applies **deterministic quality evaluation**, and enforces **explicit human approval** before any output is persisted.

Designed for **regulated and high-risk workflows** such as finance, compliance, policy analysis, and executive reporting.

---

## Why This Project Exists (Enterprise Context)

In real-world production systems, **LLMs cannot be trusted as autonomous decision-makers**.

This project demonstrates how to design AI systems where:

- LLMs generate drafts, not decisions  
- Deterministic logic evaluates quality  
- Humans retain final authority  
- Every action is logged and reproducible  

> **Core philosophy:**  
> *LLMs propose. Deterministic systems evaluate. Humans decide.*

---

## Architecture

**Design principle: Separation of generation, evaluation, and authority**

- LLM generates drafts  
- Deterministic logic evaluates quality  
- Humans retain final authority  
- All decisions are logged and reproducible  

### 📐 Architecture Diagram

<img width="8192" height="1063" alt="image" src="https://github.com/user-attachments/assets/89c3fade-12ec-46a5-8a21-1d57f6893405" />


---

## System Flow (High Level)

1. PDF ingestion and text extraction  
2. LLM-based summarization (draft only)  
3. Deterministic quality scoring  
4. Optional PII / sensitive data checks  
5. Explicit human review  
6. Approved or rejected persistence  
7. Optional reviewer-driven regeneration  

> There are **no autonomous loops** and **no self-approving AI paths**.

---

## Key Features

### 1. PDF → Text Extraction
- Extracts readable text from PDFs using `pdfplumber`.

### 2. LLM Summarization (Draft-Only)
- Uses OpenAI `chat.completions`
- Model: `gpt-4o-mini`
- Output is **never persisted directly**

### 3. Deterministic Quality Scoring
Evaluates summaries using rule-based logic:
- Coverage of key financial topics  
- Clarity via sentence-length heuristics  
- Language quality via formatting checks  

Flags:
- `flagged_uncertain`
- `flagged_too_short`

> Prevents the anti-pattern of *LLM judging LLM output*.

### 4. Human-in-the-Loop Approval
- **Approve** → stored in `approved_summaries`
- **Reject + Feedback** → stored in `rejected_summaries`

> No summary is ever stored without explicit human consent.

### 5. Auditability & Traceability
Logs include:
- UUID  
- Timestamps  
- Decision outcome  
- Quality flags  
- Model + prompt version (recommended)

### 6. Reviewer-Gated Regeneration
- Regeneration is explicitly triggered by human feedback
- The system never self-loops autonomously

---

## Environment & Secrets Management

- `.env` contains real secrets and is excluded via `.gitignore`
- `.env.example` is provided as a safe template
- Virtual environments (`venv/`) are excluded

This follows **enterprise security best practices**.

---

## Project Structure

├── main.py
├── score_logic.py
├── schema.sql
├── requirements.txt
├── README.md
├── .env.example
├── snapshots/
│ ├── uploads/
│ │ └── *.pdf
│ └── architecture.png


---

## What This Project Demonstrates (Hiring Signal)

This project intentionally demonstrates:

- Human authority over AI  
- Deterministic evaluation over probabilistic judgment  
- Safe AI patterns for regulated domains  
- Production-grade auditability  
- Clear separation of concerns  

> This is **not** a chatbot demo.  
> This is a **governed AI workflow**.

---

## Future Extensions (Not Implemented, By Design)

Possible extensions if deployed at scale:
- Role-based reviewers  
- Batch document processing  
- Analytics on rejection reasons  
- Policy-based approval thresholds  

These are intentionally excluded to keep the system **controlled, explainable, and audit-safe**.

---

## License

MIT (or your preferred license)
