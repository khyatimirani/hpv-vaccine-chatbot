import logging
import os

from dotenv import load_dotenv
from pinecone import Pinecone

logger = logging.getLogger(__name__)


class PineconeStore:
    """
    Vector database backed by Pinecone.

    Provides query and upsert operations for use in the RAG pipeline.
    Embeddings must be generated externally (e.g. via openai_embedder.embed)
    before calling these methods.
    """

    def __init__(self, index_name: str) -> None:
        """
        Initialise the Pinecone client and connect to the named index.

        Args:
            index_name: Name of the Pinecone index to use.
        """
        load_dotenv()
        api_key = (os.environ.get("PINECONE_API_KEY") or "").strip()
        if not api_key:
            raise ValueError("PINECONE_API_KEY environment variable is not set or is empty.")
        index_name = index_name.strip()
        if not index_name:
            raise ValueError("Pinecone index name must not be empty.")
        logger.info("Initialising Pinecone client (index=%r).", index_name)
        self._pc = Pinecone(api_key=api_key)
        self._index = self._pc.Index(index_name)

    def query(self, query_embedding: list[float], top_k: int = 3) -> list:
        """
        Query the Pinecone index with a pre-computed embedding.

        Args:
            query_embedding: The embedding vector for the query.
            top_k: Number of nearest neighbours to return. Defaults to 3.

        Returns:
            List of match objects with ``id``, ``score``, and ``metadata``.
        """
        response = self._index.query(
            vector=query_embedding,
            top_k=top_k,
            include_metadata=True,
        )
        return response.matches

    def upsert(self, vectors: list[dict]) -> None:
        """
        Upsert a list of vector records into the Pinecone index.

        Args:
            vectors: List of dicts with keys ``id``, ``values``, and ``metadata``.
        """
        self._index.upsert(vectors=vectors)
        logger.info("Upserted %d vector(s) to Pinecone.", len(vectors))

    def count(self) -> int:
        """
        Return the total number of vectors in the index.

        Returns:
            Total vector count across all namespaces.
        """
        stats = self._index.describe_index_stats()
        return stats.total_vector_count
