# Human-in-the-Loop Document Summarizer

## Overview

This project is an **AI-powered tool** that automatically summarizes long financial documents into shorter, clear summaries. But it also includes a **human review step** to ensure the summaries are accurate and high quality.

---

## Why This Project?

- Financial documents can be long and complicated.
- AI helps quickly generate summaries.
- But AI can make mistakes or miss important details.
- So, humans review, approve, or reject summaries and give feedback.
- This improves the overall quality and helps train better AI in the future.

---

## How It Works

1. **PDF Upload:** The user uploads a PDF financial document.
2. **Text Extraction:** The app extracts all text from the PDF.
3. **AI Summary Generation:** The text is sent to OpenAI's GPT-4o-mini model, which generates a professional summary.
4. **Scoring:** The summary is scored based on length, clarity, important topic coverage, and language quality.
5. **Human Review:** A reviewer reads the summary and decides to approve or reject it.
6. **Store Results:** Approved summaries are saved in one database table, rejected ones (with feedback) in another.
7. **Feedback Loop:** Feedback helps improve future summaries.

---

## Key Components

- **Python**: The main programming language used.
- **OpenAI API**: For generating AI-powered summaries.
- **pdfplumber**: To extract text from PDF files.
- **PostgreSQL** (via Supabase): Stores approved and rejected summaries.
- **psycopg2**: Python library to connect to PostgreSQL database.
- **dotenv**: To safely manage API keys and database credentials via `.env` file.

---

## How to Run the Project

1. **Clone this repository.**

2. **Create a `.env` file** in the root folder with these variables:
    ```env
    OPENAI_API_KEY=your_openai_api_key_here
    DB_URL=your_postgres_connection_string_here
    ```

3. **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4. **Place your PDF file** inside `snapshots/uploads/` folder or update the path in `main.py`.

5. **Run the script:**
    ```bash
    python main.py
    ```

6. **Follow the prompts** to review and approve/reject the summary.

---

## Database Structure

- **approved_summaries**
  - Stores summaries approved by reviewers.
  - Contains columns like `id`, `original_text`, `summary`, `score`, flags, reviewer info, feedback, and timestamps.

- **rejected_summaries**
  - Stores summaries rejected by reviewers along with feedback.

---

## Summary Scoring Criteria

- **Coverage:** How many key financial topics the summary covers.
- **Clarity:** Average sentence length, aiming for clear communication.
- **Language Quality:** Checks for grammar and punctuation issues.
- **Flags:** Marks summaries that are too short or uncertain.

---

## Benefits of This Project

- Combines the speed of AI with the accuracy of human judgment.
- Improves summary quality over time with feedback.
- Useful for financial advisors, analysts, or anyone dealing with large financial reports.
- Easy to adapt for other document types.

---

## Future Improvements

- Add a web interface for easier document uploads and reviewing.
- Integrate user authentication.
- Use feedback to retrain AI for better summaries.
- Support more document formats and languages.

---

## License

This project is open-source and free to use.

