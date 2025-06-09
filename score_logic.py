def score_summary(summary, original_text):
    # Flag uncertain language
    uncertain_words = ["maybe", "probably", "i think", "could", "might", "possibly"]
    flagged_uncertain = any(word in summary.lower() for word in uncertain_words)

    # Flag if summary is too short (less than 25 words)
    flagged_too_short = len(summary.split()) < 25

    # Coverage: check if key financial topics are present
    key_topics = ["asset allocation", "sip", "tax", "portfolio", "emotional", "risk", "monitor", "rebalance"]
    coverage_hits = sum(1 for topic in key_topics if topic in summary.lower())
    coverage_score = min(coverage_hits, 4)

    # Clarity: Check average sentence length (ideal: 10-20 words)
    sentences = [s.strip() for s in summary.split(".") if s.strip()]
    if sentences:
        avg_len = sum(len(s.split()) for s in sentences) / len(sentences)
        clarity_score = 3 if 10 <= avg_len <= 20 else 2
    else:
        clarity_score = 1

    # Language Quality: Look for grammar/formatting issues
    grammar_issues = ["  ", "..", " ,", ",,", " ."]
    lang_issues_found = any(issue in summary for issue in grammar_issues)
    language_score = 2 if lang_issues_found else 3

    total_score = coverage_score + clarity_score + language_score  # Max: 10

    return total_score, flagged_uncertain, flagged_too_short
