# Human-in-the-Loop Financial Document Summarizer

![Python](https://img.shields.io/badge/Python-3.10+-blue) ![Streamlit](https://img.shields.io/badge/UI-Streamlit-red) ![LLM](https://img.shields.io/badge/LLM-OpenAI-green) ![License](https://img.shields.io/badge/License-MIT-yellow)

A governed AI workflow that summarizes financial PDFs using LLMs while enforcing:

* deterministic scoring
* human approval
* audit logging
* safe persistence

Designed for regulated environments where AI assists decisions but never replaces human authority.

> **LLMs propose. Deterministic systems evaluate. Humans decide.**

---

## Architecture

<img src="assets/architecture.svg" width="1000"/>

### Mermaid Architecture Source

```mermaid
graph TB

subgraph Frontend_Layer
UI["Streamlit UI<br>Upload PDF | Generate Summary<br>Score | Approve / Reject"]
Reviewer["Human Reviewer<br>Final Authority"]
UI --> Reviewer
end

subgraph Processing_Layer
Upload["PDF Upload"]
Extract["Text Extraction<br>pdfplumber"]
Clean["Clean + Chunk Text"]
Summ["Summarization Engine<br>HF Pipeline / OpenAI"]
Score["Deterministic Scoring"]
Upload --> Extract --> Clean --> Summ --> Score
end

subgraph Governance_Layer
Gate["Human Review Gate"]
Decision{"Approve or Reject?"}
Audit["Audit Logger"]
Reviewer --> Gate
Score --> Gate
Gate --> Decision
Decision --> Audit
end

subgraph Data_Layer
Approved[(approved_summaries)]
Rejected[(rejected_summaries)]
Events[(audit_events)]
end

Decision -->|Approve| Approved
Decision -->|Reject| Rejected
Audit --> Events

classDef frontend fill:#dbeafe,stroke:#1e40af,stroke-width:2px,color:#000;
classDef processing fill:#dcfce7,stroke:#166534,stroke-width:2px,color:#000;
classDef governance fill:#fef3c7,stroke:#92400e,stroke-width:2px,color:#000;
classDef data fill:#fce7f3,stroke:#9d174d,stroke-width:2px,color:#000;

class UI,Reviewer frontend;
class Upload,Extract,Clean,Summ,Score processing;
class Gate,Decision,Audit governance;
class Approved,Rejected,Events data;
```

---

## Tech Stack

* Python
* Streamlit
* OpenAI GPT-4o / HF pipeline
* pdfplumber
* PostgreSQL / Supabase
* Deterministic scoring engine
* Audit logging layer

---


---

## Quick Start

```bash
git clone https://github.com/yourname/project.git
cd project

python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

pip install -r requirements.txt
streamlit run streamlit_app.py
```

---

## Folder Structure (Matches Your Repo)

```
project/
├── README.md
├── requirements.txt
├── schema.sql
├── main.py
├── streamlit_app.py
├── score_logic.py
├── db_smoke.py
├── keep_supabase_alive.py
└── assets/
    ├── architecture.svg
    └── screenshot1.png
```

---

## Impact

This project demonstrates production-safe AI patterns:

✅ human authority over AI
✅ deterministic validation over probabilistic trust
✅ audit-ready architecture
✅ enterprise AI governance
✅ regulated-domain workflow design

This is not a chatbot demo.
This is a governed AI system.

---

## License

MIT

---





```
assets/screenshot1.png
![Screenshot 1](assets/screenshot1.png)
![Screenshot 2](assets/screenshot2.png)

```

3. README already references it:

```md
![App Screenshot](assets/screenshot1.png)
```




