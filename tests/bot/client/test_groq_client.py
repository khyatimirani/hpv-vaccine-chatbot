from unittest.mock import MagicMock, patch

import pytest
from bot.client.groq_client import GroqClient
from bot.model.model_registry import Model, get_model_settings


@pytest.fixture
def groq_model_settings():
    return get_model_settings(Model.GROQ_LLAMA_3_1_EIGHT.value)


def _make_completion(content: str):
    """Build a mock non-streaming Groq completion object."""
    choice = MagicMock()
    choice.message.content = content
    completion = MagicMock()
    completion.choices = [choice]
    return completion


def _make_chunk(content: str):
    """Build a mock streaming Groq chunk object."""
    chunk = MagicMock()
    chunk.choices[0].delta.content = content
    return chunk


@pytest.fixture
def groq_client(groq_model_settings):
    with patch("bot.client.groq_client.Groq"), patch("bot.client.groq_client.AsyncGroq"):
        client = GroqClient(model_settings=groq_model_settings, api_key="test-key")
    return client


def test_generate_answer(groq_client):
    groq_client.client.chat.completions.create.return_value = _make_completion("Rome is the capital of Italy.")
    answer = groq_client.generate_answer("What is the capital of Italy?", max_new_tokens=50)
    assert "rome" in answer.lower()


def test_stream_answer(groq_client):
    chunks = [_make_chunk("Ro"), _make_chunk("me")]
    groq_client.client.chat.completions.create.return_value = iter(chunks)
    answer = groq_client.stream_answer("What is the capital of Italy?", max_new_tokens=50)
    assert "rome" in answer.lower()


def test_start_answer_iterator_streamer(groq_client):
    chunks = [_make_chunk("Ro"), _make_chunk("me")]
    groq_client.client.chat.completions.create.return_value = iter(chunks)
    stream = groq_client.start_answer_iterator_streamer("What is the capital of Italy?", max_new_tokens=50)
    answer = ""
    for chunk in stream:
        answer += groq_client.parse_token(chunk)
    assert "rome" in answer.lower()


def test_parse_token(groq_client):
    chunk = _make_chunk("Rome")
    assert groq_client.parse_token(chunk) == "Rome"


@pytest.mark.asyncio
async def test_async_generate_answer(groq_client):
    async def mock_create(*args, **kwargs):
        return _make_completion("Rome")

    groq_client.async_client.chat.completions.create = mock_create
    answer = await groq_client.async_generate_answer("What is the capital of Italy?", max_new_tokens=50)
    assert "rome" in answer.lower()
