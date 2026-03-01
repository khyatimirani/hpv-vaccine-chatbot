"""Tests for the Pre-RAG intent classification layer."""

import pytest
from bot.conversation.intent_classifier import (
    ABUSIVE,
    CAPABILITY_QUESTION,
    GRATITUDE,
    GREETING,
    OUT_OF_SCOPE,
    PREDEFINED_RESPONSES,
    VAGUE_QUERY,
    VALID_HEALTH_QUERY,
    classify_intent,
    get_rag_query,
)

# ---------------------------------------------------------------------------
# GREETING
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "hi",
        "Hi",
        "HI",
        "hello",
        "Hello",
        "hey",
        "namaste",
        "Namaste",
        "good morning",
        "Good Morning",
        "good evening",
        "good afternoon",
        "good night",
        "how are you",
        "hi there",
        "hello didi",
        "hi!",
        "hello.",
    ],
)
def test_classify_intent_greeting(text):
    assert classify_intent(text) == GREETING


# ---------------------------------------------------------------------------
# CAPABILITY_QUESTION
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "what do you do?",
        "who are you?",
        "how can you help me?",
        "what is this?",
        "what is HPV Vaccine Saathi?",
        "what can you do?",
        "what are you?",
        "how does this work?",
    ],
)
def test_classify_intent_capability_question(text):
    assert classify_intent(text) == CAPABILITY_QUESTION


# ---------------------------------------------------------------------------
# GRATITUDE / CLOSING
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "thank you",
        "thanks",
        "ok thanks",
        "got it",
        "bye",
        "goodbye",
        "see you",
        "take care",
        "thx",
    ],
)
def test_classify_intent_gratitude(text):
    assert classify_intent(text) == GRATITUDE


# ---------------------------------------------------------------------------
# ABUSIVE
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "you are a bitch",
        "this is bullshit, fuck this",
        "what the fuck",
    ],
)
def test_classify_intent_abusive(text):
    assert classify_intent(text) == ABUSIVE


# ---------------------------------------------------------------------------
# OUT_OF_SCOPE
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "tell me about diabetes management",
        "what is malaria?",
        "how to reduce blood pressure?",
        "who will win the election?",
        "what is my horoscope today?",
        "write python code for me",
        "what is the bitcoin price?",
        "how do I cook biryani?",
    ],
)
def test_classify_intent_out_of_scope(text):
    assert classify_intent(text) == OUT_OF_SCOPE


# ---------------------------------------------------------------------------
# VAGUE_QUERY (Edge Case A)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "vaccine",
        "vaccine?",
        "safe?",
        "dose?",
        "dose",
        "safety",
        "schedule",
    ],
)
def test_classify_intent_vague_query(text):
    assert classify_intent(text) == VAGUE_QUERY


# ---------------------------------------------------------------------------
# VALID_HEALTH_QUERY
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "is the HPV vaccine safe?",
        "how many doses of HPV vaccine are needed?",
        "what is the cervical cancer vaccination schedule?",
        "I am scared to vaccinate my daughter",
        "side effects of gardasil",
        "who is eligible for HPV vaccination in India?",
        "tell me about cervarix",
        "does the HPV vaccine cause side effects?",
        "what is human papillomavirus?",
    ],
)
def test_classify_intent_valid_health_query(text):
    assert classify_intent(text) == VALID_HEALTH_QUERY


# ---------------------------------------------------------------------------
# Edge Case B: mixed greeting + HPV question → VALID_HEALTH_QUERY
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "Hi, is HPV vaccine safe?",
        "hello, how many doses of HPV vaccine?",
        "hey tell me about cervical cancer vaccination",
        "namaste, what are the side effects of the HPV vaccine?",
    ],
)
def test_classify_intent_mixed_greeting_hpv_query(text):
    assert classify_intent(text) == VALID_HEALTH_QUERY


# ---------------------------------------------------------------------------
# Edge Case C: Emotional / anxious inputs with HPV context → VALID_HEALTH_QUERY
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "I am scared to vaccinate my daughter",
        "I am worried about the side effects of the HPV vaccine",
        "my daughter is afraid of the cervical cancer injection",
    ],
)
def test_classify_intent_emotional_hpv_query(text):
    assert classify_intent(text) == VALID_HEALTH_QUERY


# ---------------------------------------------------------------------------
# get_rag_query
# ---------------------------------------------------------------------------


def test_get_rag_query_strips_greeting_prefix():
    result = get_rag_query("Hi, is HPV vaccine safe?")
    assert "hi" not in result.lower()
    assert "hpv" in result.lower()


def test_get_rag_query_no_greeting_unchanged():
    query = "is the HPV vaccine safe?"
    assert get_rag_query(query) == query


def test_get_rag_query_strips_namaste():
    result = get_rag_query("Namaste, what is the HPV vaccine schedule?")
    assert "namaste" not in result.lower()
    assert "schedule" in result.lower()


def test_get_rag_query_preserves_original_casing():
    result = get_rag_query("Hello, What is the HPV Vaccine?")
    assert result == "What is the HPV Vaccine?"


# ---------------------------------------------------------------------------
# PREDEFINED_RESPONSES completeness
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "intent",
    [GREETING, CAPABILITY_QUESTION, GRATITUDE, ABUSIVE, OUT_OF_SCOPE, VAGUE_QUERY],
)
def test_predefined_responses_present(intent):
    assert intent in PREDEFINED_RESPONSES
    assert len(PREDEFINED_RESPONSES[intent]) > 0


# ---------------------------------------------------------------------------
# Whitespace / case normalisation
# ---------------------------------------------------------------------------


def test_classify_intent_strips_leading_trailing_whitespace():
    assert classify_intent("  hi  ") == GREETING


def test_classify_intent_case_insensitive_greeting():
    assert classify_intent("HELLO") == GREETING


def test_classify_intent_case_insensitive_health_query():
    assert classify_intent("IS THE HPV VACCINE SAFE?") == VALID_HEALTH_QUERY
