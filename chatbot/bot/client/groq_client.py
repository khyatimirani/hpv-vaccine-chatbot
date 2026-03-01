import os
from typing import Any, Iterator

from groq import AsyncGroq, Groq

from bot.client.prompt import (
    CTX_PROMPT_TEMPLATE,
    QA_PROMPT_TEMPLATE,
    REFINED_ANSWER_CONVERSATION_AWARENESS_PROMPT_TEMPLATE,
    REFINED_CTX_PROMPT_TEMPLATE,
    REFINED_QUESTION_CONVERSATION_AWARENESS_PROMPT_TEMPLATE,
    generate_conversation_awareness_prompt,
    generate_ctx_prompt,
    generate_qa_prompt,
    generate_refined_ctx_prompt,
)
from bot.model.base_groq_model import GroqModelSettings


class GroqClient:
    """
    Language model client that uses the Groq inference API.
    Provides the same interface as LamaCppClient so it can be used as a drop-in replacement.
    """

    def __init__(self, model_settings: GroqModelSettings, api_key: str | None = None):
        self.model_settings = model_settings
        api_key = api_key or os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise ValueError(
                "A Groq API key is required. Provide it via the api_key parameter "
                "or set the GROQ_API_KEY environment variable."
            )
        self.client = Groq(api_key=api_key)
        self.async_client = AsyncGroq(api_key=api_key)

    def _build_messages(self, prompt: str) -> list[dict]:
        messages = []
        if self.model_settings.system_template:
            messages.append({"role": "system", "content": self.model_settings.system_template})
        messages.append({"role": "user", "content": prompt})
        return messages

    def _extra_kwargs(self) -> dict[str, Any]:
        cfg = self.model_settings.config_answer or {}
        kwargs = {}
        if "temperature" in cfg:
            kwargs["temperature"] = cfg["temperature"]
        if "stop" in cfg and cfg["stop"]:
            kwargs["stop"] = cfg["stop"]
        return kwargs

    def generate_answer(self, prompt: str, max_new_tokens: int = 512) -> str:
        """
        Generates an answer based on the given prompt using the Groq API.

        Args:
            prompt (str): The input prompt for generating the answer.
            max_new_tokens (int): The maximum number of new tokens to generate (default is 512).

        Returns:
            str: The generated answer.
        """
        completion = self.client.chat.completions.create(
            model=self.model_settings.model_id,
            messages=self._build_messages(prompt),
            max_tokens=max_new_tokens,
            **self._extra_kwargs(),
        )
        return completion.choices[0].message.content or ""

    async def async_generate_answer(self, prompt: str, max_new_tokens: int = 512) -> str:
        """
        Generates an answer based on the given prompt using the Groq API asynchronously.

        Args:
            prompt (str): The input prompt for generating the answer.
            max_new_tokens (int): The maximum number of new tokens to generate (default is 512).

        Returns:
            str: The generated answer.
        """
        completion = await self.async_client.chat.completions.create(
            model=self.model_settings.model_id,
            messages=self._build_messages(prompt),
            max_tokens=max_new_tokens,
            **self._extra_kwargs(),
        )
        return completion.choices[0].message.content or ""

    def stream_answer(self, prompt: str, max_new_tokens: int = 512) -> str:
        """
        Generates an answer by streaming tokens from the Groq API.

        Args:
            prompt (str): The input prompt for generating the answer.
            max_new_tokens (int): The maximum number of new tokens to generate (default is 512).

        Returns:
            str: The generated answer.
        """
        answer = ""
        for chunk in self.start_answer_iterator_streamer(prompt, max_new_tokens=max_new_tokens):
            answer += self.parse_token(chunk)
            print(self.parse_token(chunk), end="", flush=True)
        return answer

    def start_answer_iterator_streamer(self, prompt: str, max_new_tokens: int = 512) -> Iterator[Any]:
        """
        Returns a streaming iterator that yields Groq response chunks.

        Args:
            prompt (str): The input prompt for generating the answer.
            max_new_tokens (int): The maximum number of new tokens to generate (default is 512).

        Returns:
            Iterator[Any]: An iterator of Groq response chunks.
        """
        return self.client.chat.completions.create(
            model=self.model_settings.model_id,
            messages=self._build_messages(prompt),
            max_tokens=max_new_tokens,
            stream=True,
            **self._extra_kwargs(),
        )

    async def async_start_answer_iterator_streamer(self, prompt: str, max_new_tokens: int = 512) -> Iterator[Any]:
        """
        Asynchronously returns a streaming iterator that yields Groq response chunks.

        Args:
            prompt (str): The input prompt for generating the answer.
            max_new_tokens (int): The maximum number of new tokens to generate (default is 512).

        Returns:
            Iterator[Any]: An iterator of Groq response chunks.
        """
        return await self.async_client.chat.completions.create(
            model=self.model_settings.model_id,
            messages=self._build_messages(prompt),
            max_tokens=max_new_tokens,
            stream=True,
            **self._extra_kwargs(),
        )

    @staticmethod
    def parse_token(chunk) -> str:
        return chunk.choices[0].delta.content or ""

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
