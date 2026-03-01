import re
from asyncio import get_event_loop
from typing import Any

from entities.document import Document
from helpers.log import get_logger

from bot.conversation.chat_history import ChatHistory
from bot.conversation.ctx_strategy import AsyncTreeSummarizationStrategy, BaseSynthesisStrategy

logger = get_logger(__name__)


def refine_question(llm: Any, question: str, chat_history: ChatHistory, max_new_tokens: int = 128) -> str:
    """
    Refines the given question based on the chat history.

    Args:
        llm (LlmClient): The language model client for conversation-related tasks.
        question (str): The original question.
        chat_history (List[Tuple[str, str]]): A list to store the conversation
        history as tuples of questions and answers.
        max_new_tokens (int, optional): The maximum number of tokens to generate in the answer.
            Defaults to 128.

    Returns:
        str: The refined question.
    """

    if chat_history:
        logger.info("--- Refining the question based on the chat history... ---")

        conversation_awareness_prompt = llm.generate_refined_question_conversation_awareness_prompt(
            question, str(chat_history)
        )

        logger.info(f"--- Prompt:\n {conversation_awareness_prompt} \n---")

        refined_question = llm.generate_answer(conversation_awareness_prompt, max_new_tokens=max_new_tokens)

        if llm.model_settings.reasoning:
            refined_question = extract_content_after_reasoning(refined_question, llm.model_settings.reasoning_stop_tag)
            if refined_question == "":
                refined_question = question

        logger.info(f"--- Refined Question: {refined_question} ---")

        return refined_question
    else:
        return question


def answer(llm: Any, question: str, chat_history: ChatHistory, max_new_tokens: int = 512) -> Any:
    """
    Generates an answer to the given question based on the chat history or a direct prompt.

    Args:
        llm (LlmClient): The language model client for conversation-related tasks.
        question (str): The input question for which an answer is generated.
        chat_history (List[Tuple[str, str]]): A list to store the conversation
        history as tuples of questions and answers.
        max_new_tokens (int, optional): The maximum number of tokens to generate in the answer.
            Defaults to 512.

    Returns:
        A streaming iterator (Any) for progressively generating the answer.

    Notes:
        The method checks if there is existing chat history. If chat history is available,
        it constructs a conversation-awareness prompt using the question and chat history.
        The answer is then generated using the LLM with the conversation-awareness prompt.
        If no chat history is available, a prompt is generated directly from the input question,
        and the answer is generated accordingly.
    """

    if chat_history:
        logger.info("--- Answer the question based on the chat history... ---")

        conversation_awareness_prompt = llm.generate_refined_answer_conversation_awareness_prompt(
            question, str(chat_history)
        )

        logger.debug(f"--- Prompt:\n {conversation_awareness_prompt} \n---")

        streamer = llm.start_answer_iterator_streamer(conversation_awareness_prompt, max_new_tokens=max_new_tokens)

        return streamer
    else:
        prompt = llm.generate_qa_prompt(question=question)
        logger.debug(f"--- Prompt:\n {prompt} \n---")
        streamer = llm.start_answer_iterator_streamer(prompt, max_new_tokens=max_new_tokens)
        return streamer


def answer_with_context(
    llm: Any,
    ctx_synthesis_strategy: BaseSynthesisStrategy,
    question: str,
    chat_history: ChatHistory,
    retrieved_contents: list[Document],
    max_new_tokens: int = 512,
):
    """
    Generates an answer to the given question using a context synthesis strategy and retrieved contents.
    If the content is not provided generates an answer based on the chat history or a direct prompt.

    Args:
        llm (LlmClient): The language model client for conversation-related tasks.
        ctx_synthesis_strategy (BaseSynthesisStrategy): The strategy to use for context synthesis.
        question (str): The input question for which an answer is generated.
        chat_history (List[Tuple[str, str]]): A list to store the conversation
        history as tuples of questions and answers.
        retrieved_contents (list[Document]): A list of documents retrieved for context.
        max_new_tokens (int, optional): The maximum number of tokens to generate in the answer. Defaults to 512.

    Returns:
        tuple: A tuple containing the answer streamer and formatted prompts.
    """
    if not retrieved_contents:
        return answer(llm, question, chat_history, max_new_tokens=max_new_tokens), []

    if isinstance(ctx_synthesis_strategy, AsyncTreeSummarizationStrategy):
        loop = get_event_loop()
        streamer, fmt_prompts = loop.run_until_complete(
            ctx_synthesis_strategy.generate_response(retrieved_contents, question, max_new_tokens=max_new_tokens)
        )
    else:
        streamer, fmt_prompts = ctx_synthesis_strategy.generate_response(
            retrieved_contents, question, max_new_tokens=max_new_tokens
        )
    return streamer, fmt_prompts


def trim_response(response: str, question: str) -> str:
    """
    Trim the response to fit within character limits based on the question intent.

    If the question contains "explain" or "detail" (case-insensitive), the response
    is trimmed to at most 512 characters. Otherwise it is trimmed to at most 200
    characters. Trimming preserves complete sentences wherever possible.

    Args:
        response: The full answer text to trim.
        question: The user question used to determine the character limit.

    Returns:
        The (possibly trimmed) response string.
    """
    question_lower = question.lower()
    is_detailed = "explain" in question_lower or "detail" in question_lower
    max_chars = 512 if is_detailed else 200

    if len(response) <= max_chars:
        return response

    trimmed = response[:max_chars]

    # Prefer trimming at the last sentence boundary within the allowed window
    last_sentence_end = max(trimmed.rfind("."), trimmed.rfind("!"), trimmed.rfind("?"))

    if last_sentence_end > max_chars // 2:
        return response[: last_sentence_end + 1]

    # Fall back to trimming at the last word boundary
    last_space = trimmed.rfind(" ")
    if last_space > max_chars // 2:
        return response[:last_space] + "…"

    return trimmed + "…"


def extract_content_after_reasoning(text: str, reasoning_stop_tag: str) -> str:
    """
    Extracts and strips the text that follows the `reasoning_stop_tag` tag.

    Args:
        text: The input string containing the tag.
        reasoning_stop_tag: The tag after which the text should be extracted.

    Returns:
        The text after the `reasoning_stop_tag` tag, stripped of whitespace, or an empty string
        if the tag is not found.
    """
    try:
        _, content = re.split(reasoning_stop_tag, text, maxsplit=1, flags=re.IGNORECASE)

        if content == "":
            logger.warning(f"Reasoning stop tag '{reasoning_stop_tag}' found but no content after it.")
        else:
            logger.info(f"Extracted content after reasoning stop tag '{reasoning_stop_tag}': {content}")

        return content.strip()
    except ValueError:
        logger.warning(f"Reasoning stop tag '{reasoning_stop_tag}' not found in the text. Returning empty content.")
        return ""


# TODO: Use it later
def stream_response_with_reasoning(
    llm: Any, user_input: str, chat_history: ChatHistory, max_new_tokens: int
) -> tuple[str, str]:
    """
    Streams a response from the language model (LLM) to the user input, including reasoning, and
    updates the UI in real-time.

    Args:
        llm (LamaCppClient): The language model client used to generate responses.
        user_input (str): The input provided by the user.
        chat_history (ChatHistory): The conversation history to provide context for the response.
        max_new_tokens (int): The maximum number of tokens to generate in the response.

    Returns:
        tuple[str, str]: A tuple containing:
            - full_response (str): The full response generated by the LLM.
            - reasoning_response (str): The reasoning portion of the response.

    Notes:
        - The function uses a placeholder to display the response progressively in the UI.
        - The reasoning portion is identified and displayed separately using start and stop tags.
        - The response is updated token by token, with a cursor ("▌") indicating ongoing generation.
    """
    import streamlit as st  # noqa: PLC0415 - imported lazily to keep module Streamlit-free

    message_placeholder = st.empty()
    full_response = ""
    reasoning_response = ""
    inside_think = False
    for token in answer(llm=llm, question=user_input, chat_history=chat_history, max_new_tokens=max_new_tokens):
        parsed_token = llm.parse_token(token)
        stripped_token = parsed_token.strip()

        if stripped_token == llm.model_settings.reasoning_start_tag:
            inside_think = True
            reasoning_response += parsed_token
            continue

        if stripped_token == llm.model_settings.reasoning_stop_tag:
            inside_think = False
            reasoning_response += parsed_token
            continue

        if inside_think:
            reasoning_response += parsed_token
        else:
            full_response += llm.parse_token(token)

        message_placeholder.markdown(reasoning_response + full_response + "▌")

    message_placeholder.markdown(reasoning_response + full_response)

    return full_response, reasoning_response
