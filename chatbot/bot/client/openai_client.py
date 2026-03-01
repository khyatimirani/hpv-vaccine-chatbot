from typing import Any, Iterator

from dotenv import load_dotenv
from openai import OpenAI

from bot.client.prompt import (
    CTX_PROMPT_TEMPLATE,
    QA_PROMPT_TEMPLATE,
    REFINED_ANSWER_CONVERSATION_AWARENESS_PROMPT_TEMPLATE,
    REFINED_CTX_PROMPT_TEMPLATE,
    REFINED_QUESTION_CONVERSATION_AWARENESS_PROMPT_TEMPLATE,
    SYSTEM_TEMPLATE,
    generate_conversation_awareness_prompt,
    generate_ctx_prompt,
    generate_qa_prompt,
    generate_refined_ctx_prompt,
)


class OpenAIModelSettings:
    """Minimal model settings descriptor for OpenAI models."""

    reasoning: bool = False
    reasoning_start_tag: str | None = None
    reasoning_stop_tag: str | None = None
    system_template: str = SYSTEM_TEMPLATE


class OpenAIClient:
    """
    Language model client backed by the OpenAI API (e.g. gpt-4o-mini).

    Exposes the same interface as LamaCppClient so it can be used as a
    drop-in replacement in the RAG pipeline.
    """

    DEFAULT_MODEL = "gpt-4o-mini"

    def __init__(self, model_name: str = DEFAULT_MODEL) -> None:
        load_dotenv()
        self.model_name = model_name
        self.model_settings = OpenAIModelSettings()
        self._client = OpenAI()

    # ------------------------------------------------------------------
    # Answer generation
    # ------------------------------------------------------------------

    def generate_answer(self, prompt: str, max_new_tokens: int = 512) -> str:
        """
        Generates a complete answer for the given prompt.

        Args:
            prompt (str): The input prompt.
            max_new_tokens (int): Maximum number of tokens to generate.

        Returns:
            str: The generated answer.
        """
        response = self._client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": self.model_settings.system_template},
                {"role": "user", "content": prompt},
            ],
            max_tokens=max_new_tokens,
        )
        return response.choices[0].message.content or ""

    async def async_generate_answer(self, prompt: str, max_new_tokens: int = 512) -> str:
        """
        Asynchronously generates a complete answer (delegates to sync version).

        Args:
            prompt (str): The input prompt.
            max_new_tokens (int): Maximum number of tokens to generate.

        Returns:
            str: The generated answer.
        """
        return self.generate_answer(prompt, max_new_tokens)

    def start_answer_iterator_streamer(
        self, prompt: str, max_new_tokens: int = 512
    ) -> Iterator[Any]:
        """
        Returns a streaming iterator that yields tokens from the OpenAI API.

        Args:
            prompt (str): The input prompt.
            max_new_tokens (int): Maximum number of tokens to generate.

        Returns:
            Iterator: A stream of response chunks.
        """
        stream = self._client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": self.model_settings.system_template},
                {"role": "user", "content": prompt},
            ],
            max_tokens=max_new_tokens,
            stream=True,
        )
        return stream

    async def async_start_answer_iterator_streamer(
        self, prompt: str, max_new_tokens: int = 512
    ) -> Iterator[Any]:
        """
        Asynchronously returns a streaming iterator (delegates to sync version).

        Args:
            prompt (str): The input prompt.
            max_new_tokens (int): Maximum number of tokens to generate.

        Returns:
            Iterator: A stream of response chunks.
        """
        return self.start_answer_iterator_streamer(prompt, max_new_tokens)

    # ------------------------------------------------------------------
    # Token parsing
    # ------------------------------------------------------------------

    @staticmethod
    def parse_token(token: Any) -> str:
        """
        Extracts the text content from a streaming chunk returned by the OpenAI API.

        Args:
            token: A streaming response chunk.

        Returns:
            str: The token content, or an empty string if there is no content.
        """
        return token.choices[0].delta.content or ""

    # ------------------------------------------------------------------
    # Prompt generation (mirrors LamaCppClient static methods)
    # ------------------------------------------------------------------

    @staticmethod
    def generate_qa_prompt(question: str) -> str:
        return generate_qa_prompt(template=QA_PROMPT_TEMPLATE, question=question)

    @staticmethod
    def generate_ctx_prompt(question: str, context: str) -> str:
        return generate_ctx_prompt(template=CTX_PROMPT_TEMPLATE, question=question, context=context)

    @staticmethod
    def generate_refined_ctx_prompt(question: str, context: str, existing_answer: str) -> str:
        return generate_refined_ctx_prompt(
            template=REFINED_CTX_PROMPT_TEMPLATE,
            question=question,
            context=context,
            existing_answer=existing_answer,
        )

    @staticmethod
    def generate_refined_question_conversation_awareness_prompt(question: str, chat_history: str) -> str:
        return generate_conversation_awareness_prompt(
            template=REFINED_QUESTION_CONVERSATION_AWARENESS_PROMPT_TEMPLATE,
            question=question,
            chat_history=chat_history,
        )

    @staticmethod
    def generate_refined_answer_conversation_awareness_prompt(question: str, chat_history: str) -> str:
        return generate_conversation_awareness_prompt(
            template=REFINED_ANSWER_CONVERSATION_AWARENESS_PROMPT_TEMPLATE,
            question=question,
            chat_history=chat_history,
        )
