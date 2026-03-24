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


def test_trim_response_explain_keyword_allows_300():
    """'explain' in question raises the limit to 300 chars (response under 300 unchanged)."""
    long_answer = "B" * 250
    result = trim_response(long_answer, "Can you explain the HPV vaccine?")
    assert len(result) == 250  # under 300, should be unchanged


def test_trim_response_detail_keyword_allows_300():
    """'detail' in question raises the limit to 300 chars (response under 300 unchanged)."""
    long_answer = "C" * 250
    result = trim_response(long_answer, "Give me detail on the HPV schedule.")
    assert len(result) == 250  # under 300, should be unchanged


def test_trim_response_explain_keyword_trims_beyond_300():
    """Even with 'explain', responses longer than 300 chars are trimmed."""
    long_answer = "D" * 400
    result = trim_response(long_answer, "Please explain HPV vaccination.")
    assert len(result) <= 300 + 1  # +1 for possible ellipsis character


def test_trim_response_describe_keyword_allows_300():
    """'describe' in question uses the 300-char detailed limit."""
    long_answer = "F" * 250
    result = trim_response(long_answer, "Can you describe the vaccine schedule?")
    assert len(result) == 250


def test_trim_response_why_keyword_allows_300():
    """'why should' in question uses the 300-char detailed limit."""
    long_answer = "G" * 250
    result = trim_response(long_answer, "Why should I get the HPV vaccine?")
    assert len(result) == 250


def test_trim_response_how_does_keyword_allows_300():
    """'how does' in question uses the 300-char detailed limit."""
    long_answer = "H" * 250
    result = trim_response(long_answer, "How does the HPV vaccine work?")
    assert len(result) == 250


def test_trim_response_preserves_sentence_boundary():
    """Trimming should end at the last sentence boundary when possible."""
    answer = ("The HPV vaccine protects against infection. " * 6).strip()
    result = trim_response(answer, "Tell me about HPV.")
    assert result.endswith(".")


def test_trim_response_case_insensitive_keywords():
    """Keyword matching is case-insensitive."""
    long_answer = "E" * 250
    assert len(trim_response(long_answer, "EXPLAIN this to me.")) == 250
    assert len(trim_response(long_answer, "Please Detail the vaccine.")) == 250


def test_trim_response_colon_para_boundary_falls_back_to_sentence():
    """When a paragraph boundary ends with ':', trimming falls back to the last sentence boundary."""
    # Build a response that is >200 chars and whose paragraph boundary ends with ":"
    intro = (
        "The HPV vaccine is generally safe, and most people do not experience serious side effects."
        " Some common and mild side effects that may occur shortly after getting the shot include:"
    )
    list_part = "\n\n- Soreness, redness, or swelling at the injection site\n- Headache\n- Fever"
    response = intro + list_part  # >200 chars total
    result = trim_response(response, "side effects of HPV")
    # Must not end with ":" (dangling list introduction) or mid-list "," 
    assert not result.endswith(":")
    assert not result.endswith(",")
    # Should end at a complete sentence
    assert result.endswith(".")


def test_trim_response_paragraph_boundary_used_when_semantically_complete():
    """A paragraph boundary that does NOT end with ':' is preferred over sentence boundary."""
    first_para = "The HPV vaccine is safe and effective. It protects against several strains."
    second_para = (
        "Studies show strong immunity after vaccination in adolescents and young adults."
        " The protection lasts for many years according to long-term follow-up research."
    )
    response = first_para + "\n\n" + second_para
    # Ensure response exceeds 200 chars
    assert len(response) > 200
    result = trim_response(response, "Tell me about the HPV vaccine.")
    # Should cut at the paragraph boundary (after first_para)
    assert result == first_para
