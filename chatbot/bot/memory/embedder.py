from chromadb.utils.embedding_functions import DefaultEmbeddingFunction


class Embedder:
    def __init__(self, **kwargs):
        """
        Initialize the Embedder using chromadb's lightweight ONNX-based embedding function.

        This embedder does NOT depend on sentence-transformers, torch, or transformers.
        For offline embedding generation (building the vector store), use
        scripts/generate_embeddings.py instead.
        """
        self.client = DefaultEmbeddingFunction()

    def embed_documents(self, texts: list[str], **kwargs) -> list[list[float]]:
        """
        Compute document embeddings.

        Args:
            texts (list[str]): The list of texts to embed.

        Returns:
            list[list[float]]: A list of embeddings, one for each text.
        """
        texts = [x.replace("\n", " ") for x in texts]
        return list(self.client(texts))

    def embed_query(self, text: str) -> list[float]:
        """
        Compute query embeddings.

        Args:
            text (str): The text to embed.

        Returns:
            list[float]: Embeddings for the text.
        """
        return self.embed_documents([text])[0]
