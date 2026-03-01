from bot.conversation.conversation_handler import extract_content_after_reasoning, trim_response


def test_extract_content_after_reasoning():
    response = "<reasoning>Some reasoning here.</reasoning> The capital of Italy is Rome."
    extracted_content = extract_content_after_reasoning(response, "</reasoning>")
    assert extracted_content.lower() == "the capital of italy is rome."


def test_extract_content_after_reasoning_missing_stop_tag():
    response = "<reasoning>Some reasoning here. The capital of Italy is Rome."
    extracted_content = extract_content_after_reasoning(response, "</reasoning>")
    assert extracted_content.lower() == ""


def test_extract_content_after_reasoning_wrong_stop_tag():
    response = "<reasoning>Some reasoning here</reasoning>. The capital of Italy is Rome."
    extracted_content = extract_content_after_reasoning(response, "</think>")
    assert extracted_content.lower() == ""


def test_extract_missing_content_after_reasoning_stop_tag():
    response = "<reasoning>Some reasoning here</reasoning>"
    extracted_content = extract_content_after_reasoning(response, "</reasoning>")
    assert extracted_content.lower() == ""


def test_extract_content_after_reasoning_case_insensitive():
    response = "<reasoning>Some reasoning here.</REASONING> The capital of Italy is Rome."
    extracted_content = extract_content_after_reasoning(response, "</reasoning>")
    assert extracted_content.lower() == "the capital of italy is rome."


def test_extract_content_after_reasoning_multiple_tags():
    response = "<reasoning>Some reasoning here.</reasoning> The capital of Italy is Rome. </reasoning> It is a city."
    extracted_content = extract_content_after_reasoning(response, "</reasoning>")
    assert extracted_content.lower() == "the capital of italy is rome. </reasoning> it is a city."


# ---------------------------------------------------------------------------
# trim_response tests
# ---------------------------------------------------------------------------


def test_trim_response_short_answer_unchanged():
    """Responses within 200 chars are returned as-is for a plain question."""
    short = "The HPV vaccine is safe."
    assert trim_response(short, "What is the HPV vaccine?") == short


def test_trim_response_default_limit_200():
    """Responses exceeding 200 chars are trimmed for a plain question."""
    long_answer = "A" * 250
    result = trim_response(long_answer, "What is HPV?")
    assert len(result) <= 200 + 1  # +1 for possible ellipsis character


def test_trim_response_explain_keyword_allows_512():
    """'explain' in question raises the limit to 512 chars."""
    long_answer = "B" * 350
    result = trim_response(long_answer, "Can you explain the HPV vaccine?")
    assert len(result) == 350  # under 512, should be unchanged


def test_trim_response_detail_keyword_allows_512():
    """'detail' in question raises the limit to 512 chars."""
    long_answer = "C" * 400
    result = trim_response(long_answer, "Give me detail on the HPV schedule.")
    assert len(result) == 400  # under 512, should be unchanged


def test_trim_response_explain_keyword_still_trims_beyond_512():
    """Even with 'explain', responses longer than 512 chars are trimmed."""
    long_answer = "D" * 600
    result = trim_response(long_answer, "Please explain HPV vaccination.")
    assert len(result) <= 512 + 1  # +1 for possible ellipsis character


def test_trim_response_preserves_sentence_boundary():
    """Trimming should end at the last sentence boundary when possible."""
    answer = ("The HPV vaccine protects against infection. " * 6).strip()
    result = trim_response(answer, "Tell me about HPV.")
    assert result.endswith(".")


def test_trim_response_case_insensitive_keywords():
    """Keyword matching is case-insensitive."""
    long_answer = "E" * 350
    assert len(trim_response(long_answer, "EXPLAIN this to me.")) == 350
    assert len(trim_response(long_answer, "Please Detail the vaccine.")) == 350
