import asyncio
from unittest.mock import MagicMock, patch

import pytest
from bot.client.openai_client import OpenAIClient, OpenAIModelSettings


@pytest.fixture
def openai_client():
    with patch("bot.client.openai_client.load_dotenv"), patch("bot.client.openai_client.OpenAI"):
        client = OpenAIClient()
    return client


# ---------------------------------------------------------------------------
# OpenAIModelSettings
# ---------------------------------------------------------------------------


def test_model_settings_defaults():
    settings = OpenAIModelSettings()
    assert settings.reasoning is False
    assert settings.reasoning_start_tag is None
    assert settings.reasoning_stop_tag is None
    assert settings.system_template != ""


# ---------------------------------------------------------------------------
# OpenAIClient initialisation
# ---------------------------------------------------------------------------


def test_default_model_name():
    with patch("bot.client.openai_client.load_dotenv"), patch("bot.client.openai_client.OpenAI"):
        client = OpenAIClient()
    assert client.model_name == "gpt-4o-mini"


def test_custom_model_name():
    with patch("bot.client.openai_client.load_dotenv"), patch("bot.client.openai_client.OpenAI"):
        client = OpenAIClient(model_name="gpt-4o")
    assert client.model_name == "gpt-4o"


def test_load_dotenv_called_on_init():
    with patch("bot.client.openai_client.load_dotenv") as mock_load_dotenv, patch(
        "bot.client.openai_client.OpenAI"
    ):
        OpenAIClient()
    mock_load_dotenv.assert_called_once()


# ---------------------------------------------------------------------------
# generate_answer
# ---------------------------------------------------------------------------


def test_generate_answer(openai_client):
    mock_response = MagicMock()
    mock_response.choices[0].message.content = "HPV vaccine is safe and effective."
    openai_client._client.chat.completions.create.return_value = mock_response

    result = openai_client.generate_answer("Is the HPV vaccine safe?", max_new_tokens=256)

    assert result == "HPV vaccine is safe and effective."
    openai_client._client.chat.completions.create.assert_called_once()
    call_kwargs = openai_client._client.chat.completions.create.call_args[1]
    assert call_kwargs["model"] == "gpt-4o-mini"
    assert call_kwargs["max_tokens"] == 256


def test_generate_answer_returns_empty_string_on_none_content(openai_client):
    mock_response = MagicMock()
    mock_response.choices[0].message.content = None
    openai_client._client.chat.completions.create.return_value = mock_response

    result = openai_client.generate_answer("test prompt")

    assert result == ""


# ---------------------------------------------------------------------------
# async_generate_answer
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_async_generate_answer(openai_client):
    mock_response = MagicMock()
    mock_response.choices[0].message.content = "Async answer."
    openai_client._client.chat.completions.create.return_value = mock_response

    result = await openai_client.async_generate_answer("test prompt")

    assert result == "Async answer."


# ---------------------------------------------------------------------------
# start_answer_iterator_streamer
# ---------------------------------------------------------------------------


def test_start_answer_iterator_streamer(openai_client):
    mock_stream = MagicMock()
    openai_client._client.chat.completions.create.return_value = mock_stream

    stream = openai_client.start_answer_iterator_streamer("test prompt", max_new_tokens=128)

    assert stream is mock_stream
    call_kwargs = openai_client._client.chat.completions.create.call_args[1]
    assert call_kwargs["stream"] is True
    assert call_kwargs["max_tokens"] == 128


# ---------------------------------------------------------------------------
# async_start_answer_iterator_streamer
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_async_start_answer_iterator_streamer(openai_client):
    mock_stream = MagicMock()
    openai_client._client.chat.completions.create.return_value = mock_stream

    stream = await openai_client.async_start_answer_iterator_streamer("test prompt")

    assert stream is mock_stream


# ---------------------------------------------------------------------------
# parse_token
# ---------------------------------------------------------------------------


def test_parse_token_returns_content():
    chunk = MagicMock()
    chunk.choices[0].delta.content = "Hello"
    assert OpenAIClient.parse_token(chunk) == "Hello"


def test_parse_token_returns_empty_string_on_none():
    chunk = MagicMock()
    chunk.choices[0].delta.content = None
    assert OpenAIClient.parse_token(chunk) == ""


# ---------------------------------------------------------------------------
# Prompt generation static methods
# ---------------------------------------------------------------------------


def test_generate_qa_prompt():
    prompt = OpenAIClient.generate_qa_prompt("What is HPV?")
    assert "What is HPV?" in prompt


def test_generate_ctx_prompt():
    prompt = OpenAIClient.generate_ctx_prompt("What is HPV?", "HPV is a virus.")
    assert "What is HPV?" in prompt
    assert "HPV is a virus." in prompt


def test_generate_refined_ctx_prompt():
    prompt = OpenAIClient.generate_refined_ctx_prompt("What is HPV?", "HPV is a virus.", "It causes cancer.")
    assert "What is HPV?" in prompt
    assert "HPV is a virus." in prompt
    assert "It causes cancer." in prompt


def test_generate_refined_question_conversation_awareness_prompt():
    prompt = OpenAIClient.generate_refined_question_conversation_awareness_prompt(
        "Is it safe?", "user asked about HPV"
    )
    assert "Is it safe?" in prompt
    assert "user asked about HPV" in prompt


def test_generate_refined_answer_conversation_awareness_prompt():
    prompt = OpenAIClient.generate_refined_answer_conversation_awareness_prompt(
        "Is it safe?", "user asked about HPV"
    )
    assert "Is it safe?" in prompt
    assert "user asked about HPV" in prompt
