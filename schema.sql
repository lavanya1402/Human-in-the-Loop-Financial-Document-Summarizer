CREATE TABLE approved_summaries (
    id UUID PRIMARY KEY,
    original_text TEXT NOT NULL,
    summary TEXT NOT NULL,
    score INTEGER NOT NULL CHECK (score BETWEEN 0 AND 10),
    flagged_uncertain BOOLEAN DEFAULT FALSE,
    flagged_too_short BOOLEAN DEFAULT FALSE,
    approved_by TEXT NOT NULL,
    feedback TEXT,
    approved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE rejected_summaries (
    id UUID PRIMARY KEY,
    original_text TEXT NOT NULL,
    rejected_summary TEXT NOT NULL,
    score INTEGER NOT NULL,
    flagged_uncertain BOOLEAN DEFAULT FALSE,
    flagged_too_short BOOLEAN DEFAULT FALSE,
    feedback TEXT NOT NULL,
    rejected_by TEXT NOT NULL,
    rejected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
