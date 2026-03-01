"""
Pre-RAG intent classification for HPV Vaccine Saathi chatbot.

Classifies user input into one of the following intents before the RAG pipeline:
  GREETING, CAPABILITY_QUESTION, GRATITUDE, ABUSIVE, OUT_OF_SCOPE, VAGUE_QUERY,
  or VALID_HEALTH_QUERY.

Only VALID_HEALTH_QUERY inputs are forwarded to the RAG pipeline.
"""

import re

# ---------------------------------------------------------------------------
# Intent constants
# ---------------------------------------------------------------------------

GREETING = "GREETING"
CAPABILITY_QUESTION = "CAPABILITY_QUESTION"
GRATITUDE = "GRATITUDE"
ABUSIVE = "ABUSIVE"
OUT_OF_SCOPE = "OUT_OF_SCOPE"
VAGUE_QUERY = "VAGUE_QUERY"
VALID_HEALTH_QUERY = "VALID_HEALTH_QUERY"

# ---------------------------------------------------------------------------
# Predefined responses
# ---------------------------------------------------------------------------

PREDEFINED_RESPONSES: dict[str, str] = {
    GREETING: (
        "Namaste 🌸 I'm your HPV Vaccine Saathi.\n\n"
        "I'm here to provide clear, trustworthy information about HPV vaccination "
        "and cervical cancer prevention in India.\n\n"
        "You can ask me about:\n"
        "• Who should take the HPV vaccine\n"
        "• Is it safe?\n"
        "• Number of doses\n"
        "• Side effects\n"
        "• Eligibility in India\n"
        "• Common myths\n\n"
        "How can I help you today?"
    ),
    CAPABILITY_QUESTION: (
        "I'm HPV Vaccine Saathi 🌸 — a public health information assistant.\n\n"
        "I provide evidence-based information about HPV vaccination, safety, eligibility, "
        "and cervical cancer prevention in India. I do not provide medical diagnosis, but I "
        "can help you understand official guidelines and common questions."
    ),
    GRATITUDE: (
        "You're most welcome 🌸\n\n"
        "If you have any more questions about HPV vaccination, I'm here to help. Take care!"
    ),
    ABUSIVE: (
        "I'm here to provide respectful and helpful information about HPV vaccination and "
        "women's health. If you have a question about that, I'll be happy to help."
    ),
    OUT_OF_SCOPE: (
        "I currently provide information specifically about HPV vaccination and cervical "
        "cancer prevention in India.\n\n"
        "For other medical or general questions, please consult a qualified healthcare professional."
    ),
    VAGUE_QUERY: (
        "Are you asking about the HPV vaccine? I can help with information about HPV vaccination in India."
    ),
}

# ---------------------------------------------------------------------------
# Pattern tables
# ---------------------------------------------------------------------------

_GREETING_EXACT = frozenset({"hi", "hello", "hey", "namaste", "hola", "howdy", "greetings"})

_GREETING_STARTS = (
    "good morning",
    "good evening",
    "good afternoon",
    "good night",
    "good day",
)

_GREETING_CONTAINS = (
    "how are you",
    "hi there",
    "hello didi",
    "namaste didi",
    "hey there",
)

_CAPABILITY_PHRASES = (
    "what do you do",
    "who are you",
    "how can you help",
    "what is this",
    "what is hpv vaccine saathi",
    "what can you do",
    "what are you",
    "how does this work",
    "what topics",
    "what questions can you",
)

_GRATITUDE_PHRASES = (
    "thank you",
    "thanks",
    "ok thanks",
    "got it",
    "bye",
    "goodbye",
    "see you",
    "take care",
    "thnks",
    "thx",
)

# Abusive terms are matched as whole words to reduce false positives.
_ABUSIVE_WORDS = re.compile(
    r"\b("
    r"fuck|shit|bitch|bastard|asshole|dick|pussy|cunt|motherfucker|whore|slut|nigger|faggot|retard"
    r"|madarchod|bhenchod|chutiya|randi|harami|gandu"
    r")\b",
    re.IGNORECASE,
)

_OUT_OF_SCOPE_INDICATORS = (
    # Other medical conditions
    "diabetes",
    "malaria",
    "typhoid",
    "dengue",
    "hypertension",
    "blood pressure",
    "heart attack",
    "stroke",
    "arthritis",
    "asthma",
    # Non-medical
    "politics",
    "election",
    "horoscope",
    "zodiac",
    "numerology",
    "astrology",
    "javascript",
    "python code",
    "programming",
    "cricket score",
    "football score",
    "recipe",
    "cooking",
    "stock market",
    "cryptocurrency",
    "bitcoin",
)

_HPV_KEYWORDS = (
    "hpv",
    "human papillomavirus",
    "cervical",
    "vaccine",
    "vaccination",
    "immuniz",
    "immunis",
    "dose",
    "doses",
    "gardasil",
    "cervarix",
    "papilloma",
    "side effect",
    "eligible",
    "eligibility",
    "cancer prevention",
    "cervix",
    "genital wart",
    "vaccinate",
)

# Single/two-word vague inputs that lack HPV context (Edge Case A).
_VAGUE_TERMS = frozenset(
    {
        "vaccine",
        "safe",
        "dose",
        "doses",
        "safety",
        "effective",
        "cost",
        "price",
        "schedule",
        "injection",
        "shot",
        "vaccine?",
        "safe?",
        "dose?",
    }
)

# Regex to strip a leading greeting word/phrase (Edge Case B).
_GREETING_PREFIX_RE = re.compile(
    r"^(hi|hello|hey|namaste|howdy|hola|greetings"
    r"|good\s+morning|good\s+evening|good\s+afternoon|good\s+night|good\s+day)"
    r"[\s,!.]*",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _is_greeting(text: str) -> bool:
    cleaned = text.strip("!.,? ")
    if cleaned in _GREETING_EXACT:
        return True
    for phrase in _GREETING_STARTS:
        if text.startswith(phrase):
            return True
    for phrase in _GREETING_CONTAINS:
        if phrase in text:
            return True
    return False


def _is_capability_question(text: str) -> bool:
    return any(phrase in text for phrase in _CAPABILITY_PHRASES)


def _is_gratitude(text: str) -> bool:
    return any(phrase in text for phrase in _GRATITUDE_PHRASES)


def _is_abusive(text: str) -> bool:
    return bool(_ABUSIVE_WORDS.search(text))


def _is_out_of_scope(text: str) -> bool:
    return any(indicator in text for indicator in _OUT_OF_SCOPE_INDICATORS)


def _contains_hpv_keywords(text: str) -> bool:
    return any(keyword in text for keyword in _HPV_KEYWORDS)


def _is_vague_single_word(text: str) -> bool:
    """Return True for very short inputs with no HPV context (Edge Case A)."""
    cleaned = text.strip("!?,. ")
    return len(cleaned.split()) <= 2 and cleaned in _VAGUE_TERMS


def _strip_greeting_prefix(text: str) -> str:
    """Remove a leading greeting word/phrase and return the remainder."""
    match = _GREETING_PREFIX_RE.match(text)
    if match:
        return text[match.end():].strip(" ,!")
    return text


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def classify_intent(user_input: str) -> str:
    """
    Classify the intent of *user_input* before sending it to the RAG pipeline.

    Returns one of: GREETING, CAPABILITY_QUESTION, GRATITUDE, ABUSIVE,
    OUT_OF_SCOPE, VAGUE_QUERY, or VALID_HEALTH_QUERY.

    Edge cases handled:
      - A: Single/two-word vague inputs without HPV context → VAGUE_QUERY.
      - B: Mixed greeting + HPV question → VALID_HEALTH_QUERY (greeting is stripped
           by :func:`get_rag_query` before calling the RAG pipeline).
      - C: Emotional/anxious inputs that contain HPV context → VALID_HEALTH_QUERY.
    """
    text = user_input.strip().lower()

    # 1. Abusive — highest priority
    if _is_abusive(text):
        return ABUSIVE

    # 2. Edge Case B — mixed greeting + HPV query
    stripped = _strip_greeting_prefix(text)
    if stripped and stripped != text and _contains_hpv_keywords(stripped):
        return VALID_HEALTH_QUERY

    # 3. Pure greeting
    if _is_greeting(text):
        return GREETING

    # 4. Capability question
    if _is_capability_question(text):
        return CAPABILITY_QUESTION

    # 5. Gratitude / closing
    if _is_gratitude(text):
        return GRATITUDE

    # 6. Out-of-scope topic
    if _is_out_of_scope(text):
        return OUT_OF_SCOPE

    # 7. Edge Case A — vague single-word with no HPV context
    if _is_vague_single_word(text):
        return VAGUE_QUERY

    # 8. HPV-related → send to RAG
    if _contains_hpv_keywords(text):
        return VALID_HEALTH_QUERY

    # Default: cannot help with this topic
    return OUT_OF_SCOPE


def get_rag_query(user_input: str) -> str:
    """
    Return the query that should be sent to the RAG pipeline.

    For Edge Case B (mixed greeting + question) the greeting prefix is stripped.
    For all other inputs the original text is returned unchanged.
    """
    text = user_input.strip()
    match = _GREETING_PREFIX_RE.match(text)
    if match:
        remaining = text[match.end() :].strip(" ,!")
        if remaining:
            return remaining
    return text
