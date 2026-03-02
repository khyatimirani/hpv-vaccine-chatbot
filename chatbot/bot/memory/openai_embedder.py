import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

_client: OpenAI | None = None


def _get_client() -> OpenAI:
    """Return a lazily-initialised OpenAI client."""
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    return _client


def embed(text: str) -> list[float]:
    """
    Generate an embedding for *text* using the OpenAI text-embedding-3-small model.

    Args:
        text: Input string to embed.

    Returns:
        Embedding as a list of floats.
    """
    response = _get_client().embeddings.create(
        model="text-embedding-3-small",
        input=text,
    )
    return response.data[0].embedding
