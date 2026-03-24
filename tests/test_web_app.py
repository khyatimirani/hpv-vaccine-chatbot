"""
Tests for chatbot/web_app.py — covering the Flask application factory and API routes.

Focus areas:
  - Vector store unavailability returns HTTP 503
  - Empty / unset PINECONE_INDEX_NAME falls back to the default index name
  - /api/chat happy-path (mocked Pinecone + OpenAI)
  - /health always returns 200
  - /api/eligibility validates input
  - /api/myth-vs-fact returns content or 404
  - /api/clear-history resets the session chat history
"""

import json
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_parameters(**overrides):
    """Return a minimal parameter namespace understood by create_app()."""
    defaults = {
        "synthesis_strategy": "stuff",
        "k": 2,
        "max_new_tokens": 512,
        "chunk_size": 1000,
        "chunk_overlap": 50,
    }
    defaults.update(overrides)
    ns = types.SimpleNamespace(**defaults)
    return ns


def _mock_ctx_strategy():
    """Return a MagicMock that behaves like a BaseSynthesisStrategy."""
    strategy = MagicMock()
    strategy.run.return_value = (iter(["answer text"]), [])
    return strategy


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def app_no_pinecone(monkeypatch, tmp_path):
    """Flask app with Pinecone initialisation forced to fail."""
    monkeypatch.delenv("PINECONE_API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
    monkeypatch.setenv("SECRET_KEY", "test-secret")

    with (
        patch("web_app.OpenAIClient") as MockLLM,
        patch("web_app.get_ctx_synthesis_strategy", return_value=_mock_ctx_strategy()),
        patch("web_app.PineconeStore", side_effect=ValueError("PINECONE_API_KEY not set")),
    ):
        MockLLM.return_value = MagicMock()
        from web_app import create_app

        flask_app = create_app(_make_parameters())
        flask_app.config["TESTING"] = True
        yield flask_app


@pytest.fixture()
def app_with_pinecone(monkeypatch, tmp_path):
    """Flask app with Pinecone mocked to succeed."""
    monkeypatch.setenv("PINECONE_API_KEY", "test-pinecone-key")
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
    monkeypatch.setenv("SECRET_KEY", "test-secret")
    # Use the default index name (no env var set)
    monkeypatch.delenv("PINECONE_INDEX_NAME", raising=False)

    mock_pinecone = MagicMock()
    mock_match = MagicMock()
    mock_match.metadata = {"text": "HPV vaccine information.", "source": "hpv.md"}
    mock_match.score = 0.9
    mock_pinecone.query.return_value = [mock_match]

    mock_llm = MagicMock()
    mock_llm.model_settings = MagicMock(reasoning=False)
    mock_llm.parse_token.side_effect = lambda t: t
    mock_strategy = MagicMock()
    mock_strategy.run.return_value = (iter(["The HPV vaccine is safe."]), [])

    with (
        patch("web_app.OpenAIClient", return_value=mock_llm),
        patch("web_app.get_ctx_synthesis_strategy", return_value=mock_strategy),
        patch("web_app.PineconeStore", return_value=mock_pinecone),
        patch("web_app.embed", return_value=[0.1] * 1536),
        patch("web_app.classify_intent", return_value="VALID_HEALTH_QUERY"),
        patch("web_app.get_rag_query", return_value="HPV vaccine safety"),
        patch("web_app.refine_question", return_value="HPV vaccine safety"),
        patch("web_app.answer_with_context", return_value=(iter(["The HPV vaccine is safe."]), [])),
        patch("web_app.VALID_HEALTH_QUERY", "VALID_HEALTH_QUERY"),
    ):
        from web_app import create_app

        flask_app = create_app(_make_parameters())
        flask_app.config["TESTING"] = True
        yield flask_app


# ---------------------------------------------------------------------------
# Tests: health
# ---------------------------------------------------------------------------


def test_health_always_200(app_no_pinecone):
    with app_no_pinecone.test_client() as client:
        resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "ok"


def test_health_200_with_pinecone(app_with_pinecone):
    with app_with_pinecone.test_client() as client:
        resp = client.get("/health")
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Tests: /api/chat — vector store unavailable
# ---------------------------------------------------------------------------


def test_chat_503_when_pinecone_unavailable(app_no_pinecone):
    """When Pinecone failed to initialise, /api/chat must return 503."""
    with app_no_pinecone.test_client() as client:
        resp = client.post("/api/chat", json={"message": "What is HPV?"})
    assert resp.status_code == 503
    body = resp.get_json()
    assert "unavailable" in body["error"].lower()


def test_chat_400_on_empty_message(app_with_pinecone):
    with app_with_pinecone.test_client() as client:
        resp = client.post("/api/chat", json={"message": ""})
    assert resp.status_code == 400


def test_chat_400_on_missing_message(app_with_pinecone):
    with app_with_pinecone.test_client() as client:
        resp = client.post("/api/chat", json={})
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Tests: /api/chat — happy path
# ---------------------------------------------------------------------------


def test_chat_happy_path(app_with_pinecone):
    with app_with_pinecone.test_client() as client:
        resp = client.post("/api/chat", json={"message": "Is the HPV vaccine safe?"})
    assert resp.status_code == 200
    body = resp.get_json()
    assert "answer" in body
    assert "sources" in body


# ---------------------------------------------------------------------------
# Tests: PINECONE_INDEX_NAME fallback
# ---------------------------------------------------------------------------


def test_pinecone_index_name_empty_string_uses_default(monkeypatch):
    """
    When PINECONE_INDEX_NAME is set to an empty string (e.g. deployer forgot
    to export the var), create_app must fall back to 'hpv-guide-v2' instead
    of passing '' to PineconeStore (which would raise ValueError).
    """
    monkeypatch.setenv("PINECONE_INDEX_NAME", "")
    monkeypatch.setenv("PINECONE_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("SECRET_KEY", "test-secret")

    captured = {}

    def fake_pinecone_store(index_name):
        captured["index_name"] = index_name
        return MagicMock()

    with (
        patch("web_app.OpenAIClient", return_value=MagicMock()),
        patch("web_app.get_ctx_synthesis_strategy", return_value=_mock_ctx_strategy()),
        patch("web_app.PineconeStore", side_effect=fake_pinecone_store),
    ):
        from web_app import create_app

        create_app(_make_parameters())

    assert captured["index_name"] == "hpv-guide-v2", (
        f"Expected fallback index 'hpv-guide-v2', got {captured['index_name']!r}"
    )


def test_pinecone_index_name_explicit_value_is_used(monkeypatch):
    """When PINECONE_INDEX_NAME is set to a non-empty value it must be used as-is."""
    monkeypatch.setenv("PINECONE_INDEX_NAME", "my-custom-index")
    monkeypatch.setenv("PINECONE_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("SECRET_KEY", "test-secret")

    captured = {}

    def fake_pinecone_store(index_name):
        captured["index_name"] = index_name
        return MagicMock()

    with (
        patch("web_app.OpenAIClient", return_value=MagicMock()),
        patch("web_app.get_ctx_synthesis_strategy", return_value=_mock_ctx_strategy()),
        patch("web_app.PineconeStore", side_effect=fake_pinecone_store),
    ):
        from web_app import create_app

        create_app(_make_parameters())

    assert captured["index_name"] == "my-custom-index"


# ---------------------------------------------------------------------------
# Tests: /api/upload-document
# ---------------------------------------------------------------------------


def test_upload_503_when_pinecone_unavailable(app_no_pinecone):
    with app_no_pinecone.test_client() as client:
        resp = client.post("/api/upload-document")
    assert resp.status_code == 503


# ---------------------------------------------------------------------------
# Tests: /api/eligibility
# ---------------------------------------------------------------------------


def test_eligibility_returns_result(app_no_pinecone):
    with app_no_pinecone.test_client() as client:
        resp = client.post(
            "/api/eligibility",
            json={"age": 14, "gender": "female", "already_vaccinated": False, "is_pregnant": False},
        )
    assert resp.status_code == 200
    body = resp.get_json()
    assert "eligible" in body
    assert "recommendation" in body


def test_eligibility_invalid_input(app_no_pinecone):
    with app_no_pinecone.test_client() as client:
        resp = client.post("/api/eligibility", json={"age": "not-a-number"})
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Tests: /api/myth-vs-fact
# ---------------------------------------------------------------------------


def test_myth_vs_fact_returns_content(app_no_pinecone, tmp_path, monkeypatch):
    myth_file = tmp_path / "docs" / "myth_vs_fact.md"
    myth_file.parent.mkdir(parents=True)
    myth_file.write_text("## Myth\nContent here.")

    import web_app as wa

    original = wa.ROOT_FOLDER
    monkeypatch.setattr(wa, "ROOT_FOLDER", tmp_path)
    try:
        with app_no_pinecone.test_client() as client:
            resp = client.get("/api/myth-vs-fact")
    finally:
        monkeypatch.setattr(wa, "ROOT_FOLDER", original)

    assert resp.status_code == 200
    assert "Content here" in resp.get_json()["content"]


def test_myth_vs_fact_404_when_file_missing(app_no_pinecone, tmp_path, monkeypatch):
    import web_app as wa

    original = wa.ROOT_FOLDER
    monkeypatch.setattr(wa, "ROOT_FOLDER", tmp_path)
    try:
        with app_no_pinecone.test_client() as client:
            resp = client.get("/api/myth-vs-fact")
    finally:
        monkeypatch.setattr(wa, "ROOT_FOLDER", original)

    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Tests: /api/clear-history
# ---------------------------------------------------------------------------


def test_clear_history(app_with_pinecone):
    with app_with_pinecone.test_client() as client:
        resp = client.post("/api/clear-history")
    assert resp.status_code == 200
    assert "cleared" in resp.get_json()["message"].lower()
