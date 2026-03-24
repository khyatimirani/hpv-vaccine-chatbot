import os
from typing import List

from dotenv import load_dotenv
from openai import OpenAI

from .openai_embedder import embed

load_dotenv()


class Embedder:
    """
    Wrapper class for OpenAI embeddings that provides the interface expected by Chroma.
    """

    def __init__(self, model_name: str = "text-embedding-3-small"):
        """
        Initialise the embedder.

        Args:
            model_name: Name of the OpenAI embedding model to use.
        """
        self.model_name = model_name
        self._client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        Embed multiple documents.

        Args:
            texts: List of text strings to embed.

        Returns:
            List of embedding vectors.
        """
        embeddings = []
        for text in texts:
            embedding = embed(text)
            embeddings.append(embedding)
        return embeddings

    def embed_query(self, text: str) -> List[float]:
        """
        Embed a single query.

        Args:
            text: Query string to embed.

        Returns:
            Embedding vector.
        """
        return embed(text)
