import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import chromadb
from chromadb.config import Settings

from ..embedder import Embedder
from .distance_metric import DistanceMetric

logger = logging.getLogger(__name__)


class Chroma:
    """
    Vector database wrapper for ChromaDB.
    
    Provides query and upsert operations for use in the RAG pipeline.
    Embeddings are generated internally using the provided Embedder.
    """

    def __init__(
        self,
        is_persistent: bool = False,
        persist_directory: Optional[str] = None,
        embedding: Optional[Embedder] = None,
        collection_name: str = "documents",
        distance_metric: DistanceMetric = DistanceMetric.COSINE,
    ) -> None:
        """
        Initialise the ChromaDB client and collection.

        Args:
            is_persistent: Whether to use persistent storage.
            persist_directory: Directory to persist the database.
            embedding: Embedder instance for generating embeddings.
            collection_name: Name of the collection to use.
            distance_metric: Distance metric to use for similarity search.
        """
        self._embedding = embedding or Embedder()
        self._collection_name = collection_name
        
        if is_persistent and persist_directory:
            # Ensure persist directory exists
            Path(persist_directory).mkdir(parents=True, exist_ok=True)
            self._client = chromadb.PersistentClient(
                path=persist_directory,
                settings=Settings(anonymized_telemetry=False)
            )
        else:
            self._client = chromadb.Client(
                settings=Settings(anonymized_telemetry=False)
            )
        
        # Get or create collection
        try:
            self._collection = self._client.get_collection(name=collection_name)
            logger.info(f"Connected to existing collection: {collection_name}")
        except Exception:
            self._collection = self._client.create_collection(
                name=collection_name,
                metadata={"hnsw:space": distance_metric.value}
            )
            logger.info(f"Created new collection: {collection_name}")

    def from_chunks(self, chunks: List[Dict[str, Any]]) -> None:
        """
        Add document chunks to the vector database.

        Args:
            chunks: List of document chunks with content and metadata.
        """
        if not chunks:
            return

        documents = []
        metadatas = []
        ids = []

        for i, chunk in enumerate(chunks):
            documents.append(chunk.page_content)
            metadatas.append(chunk.metadata or {})
            ids.append(chunk.metadata.get("id", f"doc_{i}"))

        # Generate embeddings
        embeddings = self._embedding.embed_documents(documents)

        # Add to collection
        self._collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids,
            embeddings=embeddings
        )
        
        logger.info(f"Added {len(chunks)} chunks to vector database")

    def similarity_search_with_threshold(
        self,
        query: str,
        k: int = 4,
        score_threshold: float = 0.5,
    ) -> Tuple[List[str], List[Dict[str, Any]]]:
        """
        Search for similar documents with a score threshold.

        Args:
            query: Query string to search for.
            k: Number of results to return.
            score_threshold: Minimum similarity score threshold.

        Returns:
            Tuple of (retrieved_contents, sources).
        """
        # Generate query embedding
        query_embedding = self._embedding.embed_query(query)

        # Search collection
        results = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=k,
            include=["documents", "metadatas", "distances"]
        )

        if not results["documents"][0]:
            return [], []

        documents = results["documents"][0]
        metadatas = results["metadatas"][0]
        distances = results["distances"][0]

        # Filter by threshold and prepare results
        retrieved_contents = []
        sources = []

        for doc, metadata, distance in zip(documents, metadatas, distances):
            # Convert distance to similarity score (lower distance = higher similarity)
            similarity_score = 1 - distance
            
            if similarity_score >= score_threshold:
                retrieved_contents.append(doc)
                sources.append({
                    "content": doc,
                    "metadata": metadata,
                    "score": similarity_score
                })

        return retrieved_contents, sources

    def get_indexed_documents(self) -> List[str]:
        """
        Get list of indexed document sources.

        Returns:
            List of document source names.
        """
        try:
            results = self._collection.get(include=["metadatas"])
            sources = set()
            
            for metadata in results["metadatas"] or []:
                if "source" in metadata:
                    sources.add(metadata["source"])
            
            return sorted(list(sources))
        except Exception as e:
            logger.error(f"Error getting indexed documents: {e}")
            return []

    def count(self) -> int:
        """
        Return the total number of vectors in the collection.

        Returns:
            Total vector count.
        """
        try:
            return self._collection.count()
        except Exception as e:
            logger.error(f"Error getting vector count: {e}")
            return 0

    def clear(self) -> None:
        """
        Clear all documents from the collection.
        """
        try:
            # Delete and recreate collection
            self._client.delete_collection(name=self._collection_name)
            self._collection = self._client.create_collection(
                name=self._collection_name,
                metadata={"hnsw:space": "cosine"}
            )
            logger.info(f"Cleared collection: {self._collection_name}")
        except Exception as e:
            logger.error(f"Error clearing collection: {e}")
